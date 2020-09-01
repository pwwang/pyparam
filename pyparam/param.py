"""Definition of a single parameter"""
import ast
import json
from typing import Optional, List, Any, Callable, Type, Dict
from pathlib import Path
from .utils import cast_to, parse_type, logger, TYPE_NAMES
from .defaults import POSITIONAL
from .exceptions import (
    PyParamValueError,
    PyParamTypeError,
    PyParamAlreadyExists
)

PARAM_MAPPINGS = {}

class Param: # pylint: disable=too-many-instance-attributes
    """Base class for parameter"""

    type: Optional[str] = None
    type_aliases: List[str] = []

    def __init__(self,
                 names: List[str],
                 default: Any,
                 desc: List[str],
                 prefix: str = 'auto',
                 show: bool = True,
                 required: bool = False,
                 subtype: Optional[bool] = None,
                 callback: Optional[Callable] = None,
                 **kwargs: Dict[str, Any]):
        self.names: List[str] = names
        self.default: Any = default
        self.desc: List[str] = desc
        self.prefix: str = prefix
        self.show: bool = show
        self.required: bool = required
        self.subtype: Optional[str] = subtype
        self.callback: Optional[Callable] = callback
        self._stack: List[Any] = []
        self._value_cached: Optional[Any] = None
        self._first_hit: Optional[bool, str] = False
        self._kwargs = kwargs

    def _prefix_name(self, name:str) -> str:
        """Add prefix to a name

        Args:
            name (str): Name to add prefix to

        Returns:
            str: Name with prefix added
        """
        if self.prefix == 'auto':
            return f"-{name}" if len(name) <= 1 else f"--{name}"
        return f"{self.prefix}{name}"

    @property
    def is_positional(self) -> bool:
        """Tell if this parameter is positional

        Returns:
            bool: True if it is, otherwise False.
        """
        return POSITIONAL in self.names

    def set_first_hit(self, param_type: str) -> None:
        """Set the status of first hit

        Args:
            param_type (str): The type specified on the command line when
                the paramter is hit
        """
        self._first_hit = 'reset' if param_type == 'reset' else True

    def close(self,
              next_param: Type['Param'],
              param_name: str,
              param_type: str) -> Type['Param']:
        """Close up this parameter while scanning the command line

        Args:
            next_param (Param): Next matched parameter
            param_name (str): Name of the next matched parameter
            param_type (str): Type of the next matched parameter

        Returns:
            Param: next_param is this parameter is closed otherwise this
                parameter
        """
        logger.debug("  Closing argument: %r", self.namestr())
        # if they are the same parameter
        if param_name in self.names and param_type != self.type:
            logger.warning("Type changed from %r to %r for argument %r",
                            self.type,
                            param_type,
                            self.namestr())
            return self.to(param_type)
        return next_param

    def close_end(self) -> None:
        """Close the parameter when it hits at the end of the command line or
        prior to a command"""
        if self._first_hit is True:
            logger.warning("No value provided for argument %r", self.namestr())

    def consume(self, value: Any) -> bool:
        """Consume a value

        Args:
            Value (Any): value to consume

        Returns:
            bool: True if value was consumed, otherwise False
        """
        if self._first_hit is True or not self._stack:
            self.push(value)
            return True
        return False

    def name(self, which: str, with_prefix: bool = True) -> str:
        """Get the shortest/longest name of the parameter

        A name is ensured to be returned. It does not mean it is the real
        short/long name, but just the shortest/longest name among all the names

        Args:
            which (str): Whether get the shortest or longest name
                Could use `short` or `long` for short.
            with_prefix (bool): Whether to include the prefix or not

        Returns:
            str: The shortest/longest name of the parameter
        """
        name: str = list(sorted(self.names, key=len))[
            0 if 'short' in which else -1
        ]
        if not with_prefix:
            return name
        return self._prefix_name(name)

    def namestr(self,
                sep: str = ", ",
                with_prefix: bool = True,
                sort: str = 'asc') -> str:
        """Get all names connected with a separator.

        Args:
            sep (str): The separator to connect the names
            with_prefix (bool): Whether to include the prefix or not
            sort (str|bool): Whether to sort the names by length,
                or False to not sort
        Returns:
            str: the connected names
        """
        names: list = ['POSITIONAL' if name == POSITIONAL
                       else self._prefix_name(name)
                       if with_prefix
                       else name
                       for name in (
                           self.names
                           if not sort
                           else sorted(self.names, key=len)
                           if sort == 'asc'
                           else sorted(self.names, key=lambda x: -len(x))
                       )]
        return sep.join(names)

    def typestr(self) -> str:
        """Get the string representation of the type

        Returns:
            str: the string representation of the type
        """
        if not self.subtype:
            return self.type
        return f"{self.type}:{self.subtype}"

    def to(self, to_type: str) -> Type['Param']:
        """Generate a different type of parameter using current settings

        Args:
            to_type (str): the type of paramter to generate

        Returns:
            Param: the generated parameter with different type
        """
        main_type, sub_type = parse_type(to_type)
        klass: Callable = PARAM_MAPPINGS[main_type]
        return klass(
            names=self.names,
            default=self.default,
            desc=self.desc,
            prefix=self.prefix,
            show=self.show,
            required=self.required,
            subtype=sub_type,
            callback=self.callback
        )

    @property
    def desc_with_default(self) -> Optional[List[str]]:
        """If default is not specified in desc, just to add with the default
        value"""
        if (
                self.required or
                self.default is None or (
                    self.desc and
                    any("Default:" in desc or "DEFAULT:" in desc
                        for desc in self.desc)
                )
        ):
            return None if self.desc is None else self.desc[:]

        desc: List[str] = self.desc[:] if self.desc else ['']

        if desc[0] and not desc[0][-1:].isspace():
            desc[0] += " "

        default_str: str = str(self.default) or "''"

        desc[0] += f"Default: {default_str}"
        return desc

    def push(self, item: Any) -> None:
        """Push a value into the stack for calculating"""
        if self._first_hit is True and self._stack:
            logger.warning(
                "Previous value of argument %r is overwritten with %r.",
                self.namestr(), item
            )
            self._stack = []

        if self._first_hit or not self._stack:
            self._stack.append([])
        self._stack[-1].append(item)
        self._first_hit = False

    def __repr__(self):
        return f'<{self.__class__.__name__}({self.namestr()}) @ {id(self)}>'

    def _value(self):
        """Get the organized value of this parameter

        Returns:
            any: The parsed value of thie parameter
        """

        if not self._stack:
            if self.required:
                raise PyParamValueError("Argument is required.")
            return self.default
        ret = self._stack[-1][0]
        self._stack = []
        return ret

    @property
    def value(self):
        """Return the cached value if possible, otherwise calcuate one

        @Returns:
            any: The cached value of this parameter or the newly calculated
                from stack
        """
        if self._value_cached is not None:
            return self._value_cached
        self._value_cached = self._value()
        return self._value_cached


    def apply_callback(self, all_values):
        """Apply the callback function to the value

        Args:
            all_values (Namespace): The namespace of values of all parameters

        Returns:
            Any: The value after the callback applied
        """
        if not callable(self.callback):
            return self.value

        try:
            try:
                val = self.callback(self.value, all_values)
            except TypeError:
                val = self.callback(self.value)
        except Exception as exc:
            raise PyParamTypeError(str(exc)) from None

        if isinstance(val, Exception):
            raise PyParamTypeError(str(val))
        return val

class ParamAuto(Param):
    """An auto parameter whose value is automatically casted"""

    type = 'auto'

    def _value(self):
        return cast_to(super()._value(), 'auto')

class ParamInt(Param):
    """An int parameter whose value is automatically casted into an int"""
    type = 'int'
    type_aliases = ['i']

    def _value(self):
        return int(super()._value())

class ParamFloat(Param):
    """A float parameter whose value is automatically casted into a float"""
    type = 'float'
    type_aliases = ['f']

    def _value(self):
        return float(super()._value())

class ParamStr(Param):
    """A str parameter whose value is automatically casted into a str"""
    type = 'str'
    type_aliases = ['s']

class ParamBool(Param):
    """A bool parameter whose value is automatically casted into a bool"""
    type = 'bool'
    type_aliases = ['b']

    def __init__(self,
                 names: List[str],
                 default: Any,
                 desc: List[str],
                 prefix: str = 'auto',
                 show: bool = True,
                 required: bool = False,
                 subtype: Optional[bool] = None,
                 callback: Optional[Callable] = None,
                 **kwargs: Dict[str, Any]):
        default = default or False
        try:
            cast_to(str(default), 'bool')
        except (PyParamValueError, PyParamTypeError):
            raise PyParamValueError(
                "Default value of a count argument must be a bool value or "
                "a value that can be casted to a bool value."
            ) from None

        super().__init__(names, default, desc, prefix, show, required,
                         subtype, callback, **kwargs)

    def close(self, next_param, param_name, param_type):
        logger.debug("  Closing argument: %r", self.namestr())
        self.push('true')
        return next_param

    def close_end(self):

        if self._first_hit is True:
            logger.debug("  Closing ending argument: %r", self.namestr())
            self.push('true')

    def consume(self, value):
        """Should I consume given parameter?"""
        if not self._first_hit:
            return False

        try:
            cast_to(value, 'bool')
        except (PyParamValueError, PyParamTypeError):
            # cannot cast, don't consume
            return False
        else:
            self.push(value)
            return True

    def _value(self):
        if not self._stack:
            return False

        ret = cast_to(self._stack[-1][0], 'bool')
        self._stack = []
        return ret

class ParamCount(Param):
    """A bool parameter whose value is automatically casted into a bool"""
    type = 'count'

    def __init__(self,
                 names: List[str],
                 default: Any,
                 desc: List[str],
                 prefix: str = 'auto',
                 show: bool = True,
                 required: bool = False,
                 subtype: Optional[bool] = None,
                 callback: Optional[Callable] = None,
                 **kwargs: Dict[str, Any]):
        default = default or 0
        if default != 0:
            raise PyParamValueError(
                "Default value of a count argument must be 0"
            )

        if 1 not in (len(name) for name in names):
            raise PyParamValueError(
                "Count argument must have a short name."
            )

        if 'max' in kwargs and (not isinstance(kwargs['max'], int) or
                                kwargs['max'] <= 0):
            raise PyParamValueError(
                "Argument 'max' for count argument must be a positive integer"
            )

        super().__init__(names, default, desc, prefix, show, required,
                         subtype, callback, **kwargs)

    def close(self, next_param, param_name, param_type):
        logger.debug("  Closing argument: %r", self.namestr())
        self.push('1')
        return next_param

    def close_end(self):
        if self._first_hit is True:
            logger.debug("  Closing ending argument: %r", self.namestr())
            self.push('1')

    def consume(self, value):
        """Should I consume given parameter?"""
        if not self._first_hit:
            return False

        if value.isdigit():
            self.push(value)
            return True

        return False

    def _value(self):
        val = super()._value()

        retval = None
        if str(val).isdigit():
            retval = int(val)
        else:
            for name in self.names:
                if len(name) != 1:
                    continue
                if name * len(val) == val:
                    # -vvv => name: v, value: vv
                    # len(vv) = 2, but value should be 3
                    retval = len(val) + 1
                    break
        if retval is None:
            raise PyParamValueError(
                "Expect repeated short names or an integer "
                "as count argument value."
            )
        if self._kwargs['max'] and retval > self._kwargs['max']:
            raise PyParamValueError(
                f"{retval} is greater than the max of "
                f"{self._kwargs['max']}."
            )

        return retval

class ParamPath(Param):
    """A path parameter whose value is automatically casted into a pathlib.Path
    """
    type = 'path'
    type_aliases = ['p']

    def _value(self):
        return Path(super()._value())

class ParamPy(Param):
    """A parameter whose value will be ast.literal_eval'ed"""
    type = 'py'

    def _value(self):
        return ast.literal_eval(super()._value())

class ParamJson(Param):
    """A parameter whose value will be parsed as json"""
    type = 'json'
    type_aliases = ['j']

    def _value(self):
        return json.loads(super()._value())

class ParamList(Param):
    """A parameter whose value is a list"""
    type = 'list'
    type_aliases = ['l', 'a', 'array']

    def close(self, next_param, param_name, param_type):
        logger.debug("  Closing argument: %r", self.namestr())
        return next_param

    def consume(self, value):
        """Should I consume given parameter?"""
        self.push(value)
        return True

    def push(self, item):
        """Push a value into the stack for calculating"""
        if self._first_hit == 'reset':
            self._stack = []
            self._first_hit = True
        super().push(item)

    def _value(self):
        """Get the value a list parameter"""
        ret = [
            cast_to(val, self.subtype)
            for sublist in self._stack
            for val in sublist
        ]
        self._stack = []
        return ret

class ParamChoice(Param):
    """A bool parameter whose value is automatically casted into a bool"""
    type = 'choice'
    type_aliases = ['c']

    def __init__(self,
                 names: List[str],
                 default: Any,
                 desc: List[str],
                 prefix: str = 'auto',
                 show: bool = True,
                 required: bool = False,
                 subtype: Optional[bool] = None,
                 callback: Optional[Callable] = None,
                 **kwargs: Dict[str, Any]):

        if 'choices' not in kwargs:
            raise PyParamValueError(
                "Argument 'choices' is required for ParamChoice."
            )

        if not isinstance(kwargs['choices'], (list, tuple)):
            raise PyParamValueError(
                "Argument 'choices' must be a list or a tuple."
            )

        super().__init__(names, default, desc, prefix, show, required,
                         subtype, callback, **kwargs)


    def _value(self):
        val = super()._value()

        if val not in self._kwargs['choices']:
            raise PyParamValueError(f"{val} is not "
                                    f"one of {self._kwargs['choices']}")

        self._stack = []
        return val

def register_param(param: Param) -> None:
    """Register a parameter class

    Args:
        param (Param): The param to register
            A param class should include a type
            You can also define type alias for a param type
    """
    for alias in param.type_aliases + [param.type]:
        if alias in TYPE_NAMES:
            raise PyParamAlreadyExists(
                f'Type name has already been registered: {alias}'
            )
        TYPE_NAMES[alias] = param.type

    PARAM_MAPPINGS[param.type] = param

register_param(ParamAuto)
register_param(ParamInt)
register_param(ParamStr)
register_param(ParamFloat)
register_param(ParamBool)
register_param(ParamCount)
register_param(ParamPath)
register_param(ParamPy)
register_param(ParamJson)
register_param(ParamList)
register_param(ParamChoice)
