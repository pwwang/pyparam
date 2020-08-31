"""Definition of a single parameter"""
import ast
import json
from pathlib import Path
from .utils import cast_to, parse_type
from .defaults import POSITIONAL
from .exceptions import PyParamValueError

class Param:
    """Base class for parameter"""

    type = None

    def __init__(self,
                 names,
                 default,
                 desc,
                 prefix='auto',
                 show=True,
                 required=False,
                 subtype=None,
                 callback=None):
        self.names = names
        self.default = default
        self.desc = desc
        self.prefix = prefix
        self.show = show
        self.required = required
        self.subtype = subtype
        self.callback = callback
        self._stack = []
        self._should_consume = False

    def _prefix_name(self, name):
        """Add prefix to the name"""
        if self.prefix == 'auto':
            return f"-{name}" if len(name) <= 1 else f"--{name}"
        return f"{self.prefix}{name}"

    def name(self, which, with_prefix=True):
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
        name = list(sorted(self.names, key=len))[0 if 'short' in which else -1]
        if not with_prefix:
            return name
        return self._prefix_name(name)

    def namestr(self, sep=", ", with_prefix=True, sort='asc'):
        """Get all names connected with a separator.

        Args:
            sep (str): The separator to connect the names
            with_prefix (bool): Whether to include the prefix or not
            sort (str|bool): Whether to sort the names by length,
                or False to not sort
        Returns:
            str: the connected names
        """
        names = ['POSITIONAL' if name == POSITIONAL
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

    def typestr(self):
        """Get the string representation of the type

        Returns:
            str: the string representation of the type
        """
        if not self.subtype:
            return self.type
        return f"{self.type}:{self.subtype}"

    def to(self, to_type):
        """Generate a different type of parameter using current settings

        Args:
            to_type (str): the type of paramter to generate

        Returns:
            Param: the generated parameter with different type
        """
        main_type, sub_type = parse_type(to_type)
        klass = PARAM_MAPPINGS[main_type]
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
    def desc_with_default(self):
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

        desc = self.desc[:] if self.desc else ['']

        if desc[0] and not desc[0][-1:].isspace():
            desc[0] += " "

        default_str = str(self.default) or "''"

        desc[0] += f"Default: {default_str}"
        return desc

    def push(self, item, first=False):
        """Push a value into the stack for calculating"""

        if first or not self._stack:
            self._stack.append([])
        self._stack[-1].append(item)

    def __repr__(self):
        return f'<{self.__class__.__name__}({self.namestr()}) @ {id(self)}>'

    def should_consume(self, value):
        """Should I consume given value?

        Args:
            value (str): value to check

        Returns:
            bool: True if this value should be consumed otherwise False
        """
        return not self._stack

    def value(self):
        """Get the organized value of this parameter

        Returns:
            any: The parsed value of thie parameter
        """
        if not self._stack:
            if self.required:
                raise PyParamValueError(
                    f"Argument {','.join(self.names)} is required."
                )
            return self.default
        ret = self._stack[-1][0]
        self._stack = []
        return ret

    def _apply_callback(self, val):
        return self.callback(val) if callable(self.callback) else val

class ParamAuto(Param):
    """An auto parameter whose value is automatically casted"""

    type = 'auto'

    def value(self):
        return self._apply_callback(cast_to(super().value(), 'auto'))

class ParamInt(Param):
    """An int parameter whose value is automatically casted into an int"""
    type = 'int'

    def value(self):
        return self._apply_callback(int(super().value()))

class ParamFloat(Param):
    """A float parameter whose value is automatically casted into a float"""
    type = 'float'

    def value(self):
        return self._apply_callback(float(super().value()))

class ParamStr(Param):
    """A str parameter whose value is automatically casted into a str"""
    type = 'str'

    def value(self):
        return self._apply_callback(super().value())

class ParamBool(Param):
    """A bool parameter whose value is automatically casted into a bool"""
    type = 'bool'

    def should_consume(self, value):
        """Should I consume given parameter?"""
        if self._stack:
            return False

        try:
            cast_to(value, 'bool')
        except PyParamValueError:
            # cannot cast, don't consume
            return False
        else:
            return True

    def value(self):
        if not self._stack:
            return self._apply_callback(False)

        ret = self._apply_callback(cast_to(self._stack[-1][0], 'bool'))
        self._stack = []
        return ret

class ParamCount(Param):
    """A bool parameter whose value is automatically casted into a bool"""
    type = 'count'

    def should_consume(self, value):
        """Should I consume given parameter?"""
        if self._stack:
            return False

        if value.isdigit():
            return True

        return False

    def value(self):
        val = super().value()
        if val.isdigit():
            return self._apply_callback(int(val))

        for name in self.names:
            if name * len(val) == val:
                # -vvv => name: v, value: vv
                # len(vv) = 2, but value should be 3
                return self._apply_callback(len(val) + 1)

        raise PyParamValueError("Expect repeated short names or an integer "
                                "as count argument value.")

class ParamPath(Param):
    """A path parameter whose value is automatically casted into a pathlib.Path
    """
    type = 'path'

    def value(self):
        return self._apply_callback(Path(super().value()))

class ParamPy(Param):
    """A parameter whose value will be ast.literal_eval'ed"""
    type = 'py'

    def value(self):
        return self._apply_callback(ast.literal_eval(super().value()))

class ParamJson(Param):
    """A parameter whose value will be parsed as json"""
    type = 'json'

    def value(self):
        return self._apply_callback(json.loads(super().value()))

class ParamList(Param):
    """A parameter whose value is a list"""
    type = 'list'

    def should_consume(self, value):
        """Should I consume given parameter?"""
        return True

    def push(self, item, first=False):
        """Push a value into the stack for calculating"""
        if first == 'reset':
            self._stack = []
        super().push(item, first=True)

    def value(self):
        """Get the value a list parameter"""
        ret = self._apply_callback([
            cast_to(val, self.subtype)
            for sublist in self._stack
            for val in sublist
        ])
        self._stack = []
        return ret

PARAM_MAPPINGS = dict(
    auto=ParamAuto,
    int=ParamInt,
    str=ParamStr,
    float=ParamFloat,
    bool=ParamBool,
    count=ParamCount,
    path=ParamPath,
    py=ParamPy,
    json=ParamJson,
    list=ParamList
)
