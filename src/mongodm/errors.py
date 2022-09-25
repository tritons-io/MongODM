class MongODMException(Exception):
    message: str

    def __repr__(self):
        self.__str__()

    def __str__(self):
        return self.message


class NotFound(MongODMException):
    message = 'Not found'


class InvalidSelection(MongODMException):
    message = 'Invalid selection'


class AbstractUsage(MongODMException):
    message = 'Tried to create an instance of an abstract class'
