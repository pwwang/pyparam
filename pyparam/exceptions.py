"""Exceptions used in pyparam"""

class PyParamException(Exception):
    """Base exception for pyparam"""

class PyParamUnsupportedParamType(PyParamException):
    """When specified param type is not supported"""

class PyParamAlreadyExists(PyParamException):
    """When try to add an existing parameter"""

class PyParamTypeError(PyParamException):
    """When parameter type is not supported"""

class PyParamValueError(PyParamException):
    """When parameter value is improper"""
