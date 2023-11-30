import logging
import traceback
from typing import Annotated

import pydantic
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
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if isinstance(v, str):
            return EncryptedStr(v)
        if isinstance(v, bytes):
            return v

    def encrypt(self, public_key):
        try:
            return rsa.encrypt(self.encode('utf-8'), public_key)
        except (AttributeError, rsa.pkcs1.CryptoError) as e:
            logging.error(e)
            logging.error(traceback.format_exc())
            raise RSAError()

def decrypt(data: bytes, private_key):
    try:
        return rsa.decrypt(data, private_key).decode('utf-8')
    except (AttributeError, rsa.pkcs1.CryptoError) as e:
        logging.error(e)
        logging.error(traceback.format_exc())
        raise RSAError()
