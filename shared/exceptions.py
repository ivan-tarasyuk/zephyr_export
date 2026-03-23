class ZException(Exception):
    pass


class Skipped(ZException):
    pass


class InvalidData(ZException):
    pass


class IOException(ZException):
    pass


class FileNotFound(IOException):
    pass


class RequestException(ZException):
    pass
