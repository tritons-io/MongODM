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

mongodm.set_config(AsyncIOMotorClient('mongodb://localhost:27017'), 'test')


class Entity(mongodm.MongoODMBase):
    __collection_name__ = 'my_entity'
    __protected_attributes__ = {'protected'}  # Writable on first creation, but not on updates

    title: str
    description: str
    protected: str


item = Entity(title='title', description='description', protected='protected')
await item.save()  # Commit in DB
item.dict()  # {'title': 'title', 'description': 'description', 'protected': 'protected', created_at: datetime.datetime(), updated_at: None, deleted_at: None}

db_items = await Entity.get_all()  # List of instances from db
db_items[0].title = 'modification'
await db_items[0].save()
await db_items[0].delete()

# To change multiples attributes simultaneously, pydantic constructor style
new_attributes_dict = {'title': 'edited', 'description': 'edited'}
item.set_attributes(**new_attributes_dict)  
```



The default _id field constructor is `uuid.uuid4` marshalled to a string. It is possible to change it by setting `__id_constructor__` to a callable that returns the desired type.


It will still be casted to a string before being written in the database. If you want this field to be of another type than a string in Mongo, you can set `__id_marshaller__` to any type accepted by MongoDB.


The configuration for the database can be set with `set_config()`  
You can enable soft delete by using set_config with `soft_delete=True`.
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


## Hooks
You can use hooks to execute code before or after a variety of events. The following hooks are available:

- `before_create()`: Before the object is created in the database.
- `after_create()`: After the object is created in the database.
- `before_save()`: Before the object is saved in the database, called both during creation and update operations.
- `after_save()`: After the object is saved in the database, called both during creation and update operations.
- `before_update(payload)`: Before the object is updated in the database. You can access the payload with the `payload` argument, and you MUST return it.
- `after_update()`: After the object is updated in the database
- `after_find()`: After the object is found in the database
- `before_delete()`: Before the object is deleted in the database
- `after_delete()`: After the object is deleted in the database
- `after_soft_delete()` (only if soft delete is enabled)
- `after_hard_delete()` (only if soft delete is disabled)

All the hooks must be declared as async functions. To define one you have to override the method on your class with the same signature as the hook you want to use.

```python
def before_create(self):
    self.created_at = datetime.now().isoformat()

# You must use the same method signature and return it at the end
def before_update(self, payload):
    payload['updated_at'] = datetime.now().isoformat()
    return payload
```

## Contributing

Contributions are welcome! Please open an issue or a pull request.
We are looking for reviews and feedback on the basic design of the library.

## License

[MIT](https://choosealicense.com/licenses/mit/)
