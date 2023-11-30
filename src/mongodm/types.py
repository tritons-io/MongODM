from bson import ObjectId, errors
import rsa

from mongodm.errors import RSAError


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


class EncryptedStr(str):

    def encrypt(self, public_key):
        try:
            return rsa.encrypt(self.encode('utf-8'), public_key)
        except (AttributeError, rsa.pkcs1.CryptoError):
            raise RSAError()

    def decrypt(self, private_key):
        try:
            return rsa.decrypt(self.encode('utf-8'), private_key).decode('utf-8')
        except (AttributeError, rsa.pkcs1.CryptoError):
            raise RSAError()