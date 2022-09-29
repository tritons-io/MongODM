# MongODM

MongODM is a simple, lightweight, and asynchronous Object Document Mapper for MongoDB.
It uses Pydantic and Motor.

## Installation

```bash
pip install python-mongodm
```

## Usage

```python
import mongodm
from motor.motor_asyncio import AsyncIOMotorClient

mongodm.set_config(AsyncIOMotorClient("mongodb://localhost:27017"), "my_database")

class Entity(mongodm.MongoODMBase):
    __collection_name__ = 'my_entity'
    __readonly_attributes__ = {'protected'}  # Writable on first creation, but not on updates
    title: str
    description: str
    protected: str


item = Entity(title='title', description='description', protected='protected')

await item.save()  # Send to DB
item.dict()  # {'title': 'title', 'description': 'description', 'protected': 'protected', created_at: datetime.datetime(), updated_at: None}

db_items = await Entity.get_all()  # List of documents from db
db_items[0].title = 'modification'
await db_items[0].save()
await db_items[0].delete()
```

Its possible to enable soft delete by using set_config with soft_delete=True

```python
mongodm.set_config(AsyncIOMotorClient("mongodb://localhost:27017"), "my_database", soft_delete=True)
```

Since the whole thing is based on Pydantic, you can use all the features of Pydantic.

```python
from pydantic import Field, validator

class Entity(mongodm.MongoODMBase):
    __collection_name__ = 'my_entity'
    title: str
    description: str
    protected: str = Field(default='protected', description='This is a protected field')

    @validator('title')
    def title_must_contain_space(cls, v):
        if ' ' not in v:
            raise ValueError('must contain a space')
        return v.title()
```

You can even modify the pydantic config by creating a new class that inherits from MongoODMBase and override the pydantic Config subclass.

```python
class MyBase(mongodm.MongoODMBase):
    class Config(mongodm.MongoODMBase.Config):
        allow_population_by_field_name = True

class Entity(MyBase):
    ...
```

## Contributing

Contributions are welcome! Please open an issue or a pull request.

## License

[MIT](https://choosealicense.com/licenses/mit/)
