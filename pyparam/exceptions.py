"""Exceptions used in pyparam"""


class PyParamException(Exception):
    """Base exception for pyparam"""


class PyParamTypeError(PyParamException):
    """When parameter type is not supported"""


class PyParamValueError(PyParamException):
    """When parameter value is improper"""


class PyParamNameError(PyParamException):
    """Any errors related to parameter names"""
