import traceback
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4
import logging

import pymongo
from motor.motor_asyncio import AsyncIOMotorClient

import bson.errors
from bson import ObjectId
from pydantic import BaseModel, BaseConfig, Field

from mongodm.types import ObjectIdStr, EncryptedStr, decrypt
from mongodm.errors import InvalidSelection, NotFound, AbstractUsage


logger = logging.getLogger('mongodm')


config = {
    'database_connection': AsyncIOMotorClient(),
    'database_name': 'database',
    'soft_delete': False,
    'encryption_config': {
        'public_key': '',
        'private_key': ''
    }
}


def set_config(database_connection: AsyncIOMotorClient, database_name: str, soft_delete: bool = False):
    config.update({
        'database_connection': database_connection,
        'database_name': database_name,
        'soft_delete': soft_delete
    })

def set_encryption_config(public_key: str, private_key: str):
    config['encryption_config'].update({
        'public_key': public_key,
        'private_key': private_key
    })


class MongODMBaseModel(BaseModel):

    class Config(BaseConfig):
        use_enum_values = True
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {
            datetime: lambda dt: dt.replace(tzinfo=timezone.utc)
            .isoformat()
            .replace("+00:00", "Z"),
            ObjectId: str
        }


class MongoODMBase(MongODMBaseModel):
    """
    Usage:
    >>> import mongodm
    >>> mongodm.set_config(AsyncIOMotorClient('mongodb://localhost:27017'), 'test')
    >>>
    >>> class Entity(mongodm.MongoODMBase):
    >>>     __collection_name__ = 'my_entity'
    >>>     __protected_attributes__ = {'protected'}  # Writable on first creation, but not on updates
    >>>
    >>>     title: str
    >>>     description: str
    >>>     protected: str
    >>>
    >>> item = Entity(title='title', description='description')
    >>> await item.save()  # Commit in DB
    >>> db_items = await Entity.get_all()  # List of instances from db
    >>> db_items[0].title = 'modification'
    >>> await db_items[0].save()
    >>> await db_items[0].delete()
    >>>
    >>> update_dict = {'title': 'edited','description': 'edited'}
    """

    id: Optional[str] = Field(alias="_id")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None

    __protected_attributes__: set = set()
    __id_marshaller__ = str
    __id_constructor__ = uuid4

    def __id_factory__(self):
        return MongoODMBase.__id_marshaller__(MongoODMBase.__id_constructor__())

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
            return cls.cast_to_object_id(item)

        if type(item) in [list]:
            return [cls.replace_str_with_object_id(i) for i in item]

        if type(item) in [dict]:
            for key in item.keys():
                if isinstance(item[key], list):
                    item[key] = [cls.replace_str_with_object_id(i) for i in item[key]]
                if isinstance(item[key], dict):
                    item[key] = cls.replace_str_with_object_id(item[key])
        return item

    @classmethod
    def encrypt_encrypted_fields(cls, item):
        if isinstance(item, EncryptedStr):
            return item.encrypt(config['encryption_config']['public_key'])

        if isinstance(item, list):
            return [cls.encrypt_encrypted_fields(i) for i in item]

        if isinstance(item, dict):
            for key in item.keys():
                if isinstance(item[key], list):
                    item[key] = [cls.encrypt_encrypted_fields(i) for i in item[key]]
                else:
                    item[key] = cls.encrypt_encrypted_fields(item[key])
        return item

    @classmethod
    def decrypt_encrypted_fields(cls, item):
        if isinstance(item, bytes):
            try:
                return decrypt(item, config['encryption_config']['private_key'])
            except Exception as e:
                return item

        if isinstance(item, list):
            return [cls.decrypt_encrypted_fields(i) for i in item]

        if isinstance(item, dict):
            for key in item.keys():
                if isinstance(item[key], list):
                    item[key] = [cls.decrypt_encrypted_fields(i) for i in item[key]]
                else:
                    item[key] = cls.decrypt_encrypted_fields(item[key])
        return item

    @classmethod
    def _get_fetch_filter(cls, selector):
        if config["soft_delete"]:
            selector["deleted_at"] = None
        return selector

    def _get_dict_with_oid(self, exclude=False, creation=False, exclude_none=False, exclude_unset=False):
        to_exclude = {"updated_at", "deleted_at"}
        if not creation:
            to_exclude.add("created_at")
        if exclude:
            to_exclude = to_exclude.union(self.__protected_attributes__)
        dump = self.dict(by_alias=True, exclude=to_exclude, exclude_none=exclude_none, exclude_unset=exclude_unset)
        dump = self.encrypt_encrypted_fields(dump)
        dump = self.replace_str_with_object_id(dump)
        return dump

    async def before_create(self):
        """ Before create hook """
        pass

    async def _create(self):
        await self.before_create()
        self.id = self.__id_factory__()
        await self.before_save()
        await config['database_connection'][config['database_name']][self.__collection_name__].insert_one(
            self._get_dict_with_oid(creation=True)
        )
        await self.after_save()
        logger.debug(f"Created {self.__collection_name__} with id {self.id}")
        await self.after_create()
        return self

    async def after_create(self):
        """ After create hook """
        pass

    async def after_find(self):
        """
        This hook is called after EVERY method that returns a single instance of the model and for every instance that
        is returned by a method that returns a list of instances.
        """
        pass

    @classmethod
    async def get_by_id(cls,
        item_id,
        projection: dict = None
    ):  # -> Self
        try:
            item = await config['database_connection'][config['database_name']][cls.__collection_name__].find_one(
                cls._get_fetch_filter({"_id": item_id}),
                projection=projection
            )
        except bson.errors.InvalidId:
            raise InvalidSelection
        if item:
            item = cls.decrypt_encrypted_fields(item)
            e = cls(**item)
            await e.after_find()
            return e
        raise NotFound

    @classmethod
    async def get_by_fields(
        cls,
        projection: dict = None,
        **kwargs
    ):  # -> Self
        fields = cls.replace_str_with_object_id(kwargs)
        try:
            item = await config['database_connection'][config['database_name']][cls.__collection_name__].find_one(
                cls._get_fetch_filter(fields),
                projection=projection
            )
        except bson.errors.InvalidId:
            raise InvalidSelection
        if item:
            item = cls.decrypt_encrypted_fields(item)
            e = cls(**item)
            await e.after_find()
            return e
        raise NotFound

    @classmethod
    async def get_with_selector(
        cls,
        selector,
        projection: dict = None
    ):  # -> Self
        mongo_selector = cls.replace_str_with_object_id(selector)
        try:
            item = await config['database_connection'][config['database_name']][cls.__collection_name__].find_one(
                cls._get_fetch_filter(mongo_selector),
                projection=projection
            )
        except bson.errors.InvalidId:
            raise InvalidSelection
        if item:
            item = cls.decrypt_encrypted_fields(item)
            e = cls(**item)
            await e.after_find()
            return e
        raise NotFound

    async def after_get_many_hook(self):
        await self.after_find()
        return self

    @classmethod
    async def count(cls, selector: dict = None, **kwargs):
        if selector is None:
            selector = kwargs
        mongo_selector = cls.replace_str_with_object_id(selector)
        return await config['database_connection'][config['database_name']][cls.__collection_name__].count_documents(
            cls._get_fetch_filter(mongo_selector)
        )

    @classmethod
    async def get_all(
        cls,
        page: int = 1,
        per_page: int = 20,
        selector: dict = None,
        projection: dict = None,
        sort: dict = None,
        **kwargs,
    ) -> list:  # -> List[Self]
        if selector is None:
            selector = kwargs
        if sort is None:
            sort = [("created_at", pymongo.DESCENDING)]
        selector = cls.replace_str_with_object_id(selector)
        items = await config['database_connection'][config['database_name']][cls.__collection_name__]\
            .find(cls._get_fetch_filter(selector), projection=projection)\
            .sort(sort)\
            .skip((page - 1) * per_page)\
            .limit(per_page)\
            .to_list(length=None)

        return [await cls(**cls.decrypt_encrypted_fields(item)).after_get_many_hook() for item in items]

    async def before_save(self):
        """ Before save hook """
        pass

    async def before_update(self, payload):
        return payload

    async def save(self, exclude_none=False, exclude_unset=False):  # -> Self
        create = False
        if self.id is None:
            create = True
            return await self._create()
        await self.before_save()
        payload = self._get_dict_with_oid(exclude=True, exclude_none=exclude_none, exclude_unset=exclude_unset)
        update_timestamp = datetime.now()
        self.updated_at = payload['updated_at'] = update_timestamp
        if not create:
            payload = await self.before_update(payload)
        await config['database_connection'][config['database_name']][self.__collection_name__].update_one(
            self.__class__._get_fetch_filter({"_id": self.__id_marshaller__(self.id)}),
            {"$set": payload},
        )
        if not create:
            await self.after_update()
        await self.after_save()
        return self

    async def after_update(self):
        """ After update hook """
        pass

    async def after_save(self):
        """ After save hook """
        pass

    async def before_delete(self):
        """ Before delete hook """
        pass

    async def delete(self):
        await self.before_delete()
        if config["soft_delete"]:
            await self._soft_delete()
        else:
            await self._hard_delete()
        await self.after_delete()

    async def after_delete(self):
        """ After delete hook """
        pass

    async def _soft_delete(self):
        await config['database_connection'][config['database_name']][self.__collection_name__].update_one(
            self.__class__._get_fetch_filter({"_id": self.__id_marshaller__(self.id)}),
            {"$set": {"deleted_at": datetime.now()}},
        )
        await self.after_soft_delete()

    async def after_soft_delete(self):
        """ After soft delete hook """
        pass

    async def _hard_delete(self):
        await config['database_connection'][config['database_name']][self.__collection_name__].delete_one(
            {"_id": self.__id_marshaller__(self.id)}
        )
        await self.after_hard_delete()

    async def after_hard_delete(self):
        """ After hard delete hook """
        pass
