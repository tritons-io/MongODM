from bson import ObjectId, errors


class ObjectIdStr(str):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        v = ObjectId(v)
        if not isinstance(v, ObjectId):
            raise ValueError("Not a valid ObjectId")
        return str(v)

    @classmethod
    def is_object_id(cls, v):
        try:
            v = ObjectId(v)
        except errors.InvalidId:
            return False
        if not isinstance(v, ObjectId):
            return False
        return True
