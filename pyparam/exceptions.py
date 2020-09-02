"""Exceptions used in pyparam"""

class PyParamException(Exception):
    """Base exception for pyparam"""

class PyParamAlreadyExists(PyParamException):
    """When try to add an existing parameter"""

class PyParamTypeError(PyParamException, TypeError):
    """When parameter type is not supported"""

class PyParamValueError(PyParamException, ValueError):
    """When parameter value is improper"""

class PyParamNameError(PyParamException, NameError):
    """Any errors related to parameter names"""
