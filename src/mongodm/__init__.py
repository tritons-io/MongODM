from datetime import datetime, timezone
from typing import Optional, Union
from motor.motor_asyncio import AsyncIOMotorClient

import bson.errors
from bson import ObjectId
from pydantic import BaseModel, BaseConfig, Field

from mongodm.types import ObjectIdStr
from mongodm.errors import InvalidSelection, NotFound, AbstractUsage


config = {
    'database_connection': None,
    'database_name': None,
    'soft_delete': False
}


def set_config(database_connection: AsyncIOMotorClient, database_name: str, soft_delete: bool = False):
    config.update({
        'database_connection': database_connection,
        'database_name': database_name,
        'soft_delete': soft_delete
    })


class MongODMBaseModel(BaseModel):

    class Config(BaseConfig):
        allow_population_by_alias = True
        arbitrary_types_allowed = True
        strict_mode = False
        json_encoders = {
            datetime: lambda dt: dt.replace(tzinfo=timezone.utc)
            .isoformat()
            .replace("+00:00", "Z"),
            ObjectId: str
        }


class MongoODMBase(MongODMBaseModel):
    """
    Usage:
    >>> set_config(AsyncIOMotorClient(), 'my-database')
    >>>
    >>> class Entity(MongoODMBase):
    >>>     __collection_name__ = 'demo_item'
    >>>     __protected_attributes__ = {'protected'}  # Writable on first creation, but not on updates
    >>>
    >>>     title: str
    >>>     description: str
    >>>     protected: str
    >>>
    >>> item = Entity(title='title', description='description')
    >>> await item.save()  # Send to DB
    >>> db_items = await Entity.get_all()  # List of instances from db
    >>> db_items[0].title = 'modification'
    >>> await db_items[0].save()
    >>> await db_items[0].delete()
    """
    id: Optional[ObjectIdStr] = Field(alias="_id", default=None)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None


    __protected_attributes__: set = set()

    @property
    def __collection_name__(self):
        raise AbstractUsage("You must define a collection name for your model")

    @staticmethod
    def cast_to_object_id(value):
        if ObjectIdStr.is_object_id(value):
            value = ObjectId(value)
        return value

    @classmethod
    def replace_str_with_object_id(cls, item):
        if type(item) in [bytes, str, ObjectId, ObjectIdStr]:
            item = cls.cast_to_object_id(item)
        if isinstance(item, list):
            item = [cls.replace_str_with_object_id(i) for i in item]
        if isinstance(item, dict):
            item = {k: cls.replace_str_with_object_id(v) for k, v in item.items()}
        return item

    @classmethod
    def _get_fetch_filter(cls, selector):
        if not config['soft_delete']:
            selector['deleted_at'] = None
        return selector

    def _get_dict_with_oid(self, exclude=False, creation=False):
        to_exclude = {'id', 'updated_at', 'deleted_at'}
        if not creation:
            to_exclude.add('created_at')
        if exclude:
            to_exclude = to_exclude.union(self.__protected_attributes__)
        return self.replace_str_with_object_id(self.dict(by_alias=True, exclude=to_exclude))

    async def _create(self):
        req = await self.config['database_connection'][config['database_name']][self.__collection_name__].insert_one(
            self._get_dict_with_oid(creation=True)
        )
        self.id = ObjectIdStr(req.inserted_id)
        return self

    @classmethod
    async def get_by_id(cls, item_id):  # -> Self
        try:
            item = await cls.config['database_connection'][config['database_name']][cls.__collection_name__].find_one(cls._get_fetch_filter({"_id": ObjectId(item_id)}))
        except bson.errors.InvalidId:
            raise InvalidSelection
        if item:
            return cls(**item)
        raise NotFound

    @classmethod
    async def get_by_fields(cls, **kwargs):  # -> Self
        fields = cls.replace_str_with_object_id(kwargs)
        try:
            item = await cls.config['database_connection'][config['database_name']][cls.__collection_name__].find_one(cls._get_fetch_filter(fields))
        except bson.errors.InvalidId:
            raise InvalidSelection
        if item:
            return cls(**item)
        raise NotFound

    @classmethod
    async def get_with_selector(cls, selector):  # -> Self
        mongo_selector = cls.replace_str_with_object_id(selector)
        try:
            item = await cls.config['database_connection'][config['database_name']][cls.__collection_name__].find_one(cls._get_fetch_filter(mongo_selector))
        except bson.errors.InvalidId:
            raise InvalidSelection
        if item:
            return cls(**item)
        raise NotFound

    @classmethod
    async def get_all(cls, page: int = 1, per_page: int = 20, selector_z: dict = None, **kwargs) -> list:  # -> List[Self]
        if selector_z is None:
            selector_z = kwargs
        selector_z = cls.replace_str_with_object_id(selector_z)
        items = await cls.config['database_connection'][config['database_name']][cls.__collection_name__].find(cls._get_fetch_filter(selector_z)).skip((page - 1) * per_page).limit(
            per_page).to_list(length=None)

        return [cls(**item) for item in items]

    async def save(self, skip_update_at: bool = False):  # -> Self
        if self.id is None:
            return await self._create()
        payload = self._get_dict_with_oid(exclude=True)
        if not skip_update_at:
            payload['updated_at'] = datetime.now()
        await self.config['database_connection'][config['database_name']][self.__collection_name__].update_one(
            self.__class__._get_fetch_filter({"_id": ObjectId(self.id)}),
            {'$set': payload}
        )
        return self

    async def delete(self):
        if config['soft_delete']:
            await self._soft_delete()
        else:
            await self._hard_delete()

    async def _soft_delete(self):
        await self.config['database_connection'][config['database_name']][self.__collection_name__].update_one(
            self.__class__._get_fetch_filter({"_id": ObjectId(self.id)}),
            {'$set': {'deleted_at': datetime.now()}}
        )

    async def _hard_delete(self):
        await self.config['database_connection'][config['database_name']][self.__collection_name__].delete_one({"_id": ObjectId(self.id)})

