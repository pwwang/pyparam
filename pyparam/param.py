"""Definition of a single parameter

Attributes:
    PARAM_MAPPINGS: The type to Param mappings, used for params to init a
        parameter. Managed by `register_param`
"""
import ast
import json
import re
from itertools import product
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Set, Tuple, Type, Union

from diot import OrderedDiot

from .completer import CompleterParam
from .defaults import ARGUMENT_REQUIRED, POSITIONAL
from .exceptions import (
    PyParamException,
    PyParamNameError,
    PyParamTypeError,
    PyParamValueError,
)
from .utils import TYPE_NAMES, Namespace, cast_to, logger, parse_type

PARAM_MAPPINGS: Dict[str, Type["Param"]] = {}


class Param(CompleterParam):
    """Base class for parameter

    Args:
        names: The names of the parameter
        default: The default value
        desc: The description of the parameter
        prefix: The prefix of the parameter on the command line
        show: Whether this parameter should show on help page
        required: Whether this parameter is required
        subtype: The subtype of the parameter if
            this is a complex type
        type_frozen: Whether the type is frozen
            (not allowing overwritting from command line)
        callback: The callback to modify the final value
        argname_shorten: Whether show shortened name for parameters
            under namespace parameters
        complete_callback: The callback for complete the values of the
            parameter
        **kwargs: Additional keyword arguments

    Attributes:
        names: The names of the parameter
        default: The default value
        prefix: The prefix of the parameter on the command line
        show: Whether this parameter should show on help page
        required: Whether this parameter is required
        subtype: The subtype of the parameter if this is a complex type
        type_frozen: Whether the type is frozen
            (not allowing overwritting from command line)
        callback: The callback to modify the final value
        argname_shorten: Whether show shortened name for the parameters
            under namespace parameters
        hit: Whether the parameter is just hit
        ns_param: The namespace parameter where this parameter
            is under
        complete_callback: The callback for complete the values of the
            parameter
        is_help: Whether this is a help parameter
        _desc: The raw description of the parameter
        _stack: The stack to push the values
        _value_cached: The cached value calculated from the stack
        _kwargs: other kwargs
    """

    type: str = None
    type_aliases: List[str] = []

    @classmethod
    def on_register(cls):
        """Opens opportunity to do something when a parameter is registered"""

    def __init__(
        self,
        names: Union[str, List[str]],
        default: Any,
        desc: List[str],
        prefix: str = "auto",
        show: bool = True,
        required: bool = False,
        subtype: Union[str, bool] = None,
        type_frozen: bool = True,
        callback: Callable = None,
        complete_callback: Callable = None,
        argname_shorten: bool = True,
        **kwargs: Dict[str, Any],
    ):
        """Constructor"""
        self.names = names
        self.default = default
        self.prefix: str = prefix
        self.show: bool = show
        self.required: bool = required
        self.subtype = subtype
        self.type_frozen: bool = type_frozen
        self.callback: Callable = callback
        self.complete_callback: Callable = complete_callback
        self.argname_shorten: bool = argname_shorten
        self.hit: bool = False
        self.is_help: bool = False
        self.ns_param: "ParamNamespace" = None
        self._desc: List[str] = desc or ["No description."]
        self._stack: List[Any] = []
        self._value_cached: Any = None
        self._kwargs: Dict[str, Any] = kwargs

        # check if I am under a namespace
        # Type: List[List[str]], List[str]
        self._namespaces, self.terminals = self._extract_namespaces()

    def _extract_namespaces(self) -> Tuple[List[List[str]], List[str]]:
        """Extract the namespace and terminal names"""
        nparts: Set[int] = set()
        namespaces: List[Set[str]] = []
        terminals: Set[str] = set()
        for name in self.names:
            parts: List[str] = name.split(".")
            nparts.add(len(parts))
            if len(nparts) > 1:
                raise PyParamNameError(
                    "Parameter names must have the same number of namespaces."
                )
            namespaces = namespaces or [{part} for part in parts[:-1]]
            for i, part in enumerate(parts[:-1]):
                namespaces[i].add(part)
            terminals.add(parts[-1])
        return [list(ns) for ns in namespaces], list(terminals)

    def _prefix_name(self, name: str) -> str:
        """Add prefix to a name

        Args:
            name: Name to add prefix to

        Returns:
            Name with prefix added
        """
        name_to_check: str = name.split(".", 1)[0]
        if self.prefix == "auto":
            return f"-{name}" if len(name_to_check) <= 1 else f"--{name}"
        return f"{self.prefix}{name}"

    def namespaces(
        self, index: Union[int, str] = "len"
    ) -> Union[List[str], int]:
        """Get the namespaces at the given index or number of namespaces

        Args:
            index: The index or a length indicator

        Returns:
            The length of the namespaces or the namespaces at index.
        """
        if index == "len":
            return len(self._namespaces)
        try:
            return self._namespaces[index]  # type: ignore
        except IndexError:
            return []

    def full_names(self) -> List[str]:
        """make the names with full combinations of namespaces and terminals

        Since one can define a parameter like `n.arg` but namespace `n` can
        have aliases (i.e. `ns`). This makes sure the names of `n.arg` expands
        to `n.arg` and `ns.arg`

        Returns:
            The names with full combinations of namespaces and terminals
        """
        self.names = [
            ".".join(prod)
            for prod in product(*self._namespaces, self.terminals)
        ]
        return self.names

    @property
    def is_positional(self) -> bool:
        """Tell if this parameter is positional

        Returns:
            True if it is, otherwise False.
        """
        return POSITIONAL in self.names

    def close(self) -> None:
        """Close up the parameter while scanning the command line

        We are mostly doing nothing, only if, say, param is bool and
        it was just hit, we should push a true value to it.
        """
        if self.hit:
            logger.warning("No value provided for argument %r", self.namestr())

    def overwrite_type(self, param_type: str) -> "Param":
        """Try to overwrite the type

        Only when param_type is not None and it's different from mine
        A new param will be returned if different

        Args:
            param_type: The type to overwrite

        Returns:
            Self when type not changed otherwise a new parameter with
                the given type
        """
        if param_type is None or param_type == self.typestr():
            return self

        if self.type_frozen:
            raise PyParamTypeError(
                f"Type of argument {self.namestr()!r} " "is not overwritable"
            )
        logger.warning(
            "Type changed from %r to %r for argument %r",
            self.typestr(),
            param_type,
            self.namestr(),
        )
        return self.to(param_type)

    def consume(self, value: Any) -> bool:
        """Consume a value

        Args:
            Value: value to consume

        Returns:
            True if value was consumed, otherwise False
        """
        if self.hit or not self._stack:
            self.push(value)
            return True
        return False

    @property
    def desc(self) -> List[str]:
        """The formatted description using attributes and _kwargs"""
        format_data: dict = {
            key: val
            for key, val in self.__dict__.items()
            if (
                not key.startswith("_") and key != "desc" and not callable(val)
            )
        }
        format_data.update(self._kwargs)
        ret: List[str] = []
        for descr in self._desc:
            try:
                descr = descr.format(**format_data)
            except KeyError as kerr:
                raise PyParamException(
                    f"Description of {self.namestr()!r} is formatting "
                    "using kwargs from contructor. \n"
                    "If you have curly braces in it, which is not intended "
                    "for formatting, please escape it by replacing with "
                    "`{{` or `}}`:\n"
                    f"- desc: {descr}\n"
                    f"- key : {{... {str(kerr)[1:-1]} ...}}"
                ) from None
            else:
                ret.append(descr)
        return ret

    def name(self, which: str, with_prefix: bool = True) -> str:
        """Get the shortest/longest name of the parameter

        A name is ensured to be returned. It does not mean it is the real
        short/long name, but just the shortest/longest name among all the names

        Args:
            which: Whether get the shortest or longest name
                Could use `short` or `long` for short.
            with_prefix: Whether to include the prefix or not

        Returns:
            The shortest/longest name of the parameter
        """
        name: str = list(sorted(self.names, key=len))[
            0 if "short" in which else -1
        ]
        return name if not with_prefix else self._prefix_name(name)

    def namestr(self, sep: str = ", ", with_prefix: bool = True) -> str:
        """Get all names connected with a separator.

        Args:
            sep: The separator to connect the names
            with_prefix: Whether to include the prefix or not
        Returns:
            the connected names
        """
        names: list = [
            "POSITIONAL"
            if name == POSITIONAL
            else self._prefix_name(name)
            if with_prefix
            else name
            for name in sorted(self.names, key=len)
        ]
        return sep.join(names)

    def typestr(self) -> str:
        """Get the string representation of the type

        Returns:
            the string representation of the type
        """
        return self.type if not self.subtype else f"{self.type}:{self.subtype}"

    def usagestr(self) -> str:
        """Get the string representation of the parameter in the default usage
        constructor

        Returns:
            the string representation of the parameter in the default usage
        """
        # * makes sure it's not wrapped
        ret: str = self.name("long") + "*"
        ret += self.typestr().upper() if self.type_frozen else self.typestr()
        return ret

    def optstr(self) -> str:
        """Get the string representation of the parameter names and types
        in the optname section in help page

        Returns:
            the string representation of the parameter names and types
                in the optname section in help page
        """
        typestr: str = (
            self.typestr().upper() if self.type_frozen else self.typestr()
        )
        if not self.ns_param or not self.argname_shorten:
            # * makes sure it's not wrapped
            return (
                self.namestr()
                if self.is_help
                else f"{self.namestr()}*<{typestr}>"
            )

        ret: List[str] = []
        for term in sorted(self.terminals, key=len):
            ret.append(f"~<ns>.{term}")
        return ", ".join(ret) + f"*<{typestr}>"

    def to(self, to_type: str) -> "Param":
        """Generate a different type of parameter using current settings

        Args:
            to_type: the type of parameter to generate

        Returns:
            the generated parameter with different type
        """
        main_type, sub_type = parse_type(to_type)
        klass: Callable = PARAM_MAPPINGS[main_type]
        param: "Param" = klass(
            names=self.names,
            default=None,
            desc=self.desc,
            prefix=self.prefix,
            show=self.show,
            required=self.required,
            subtype=sub_type,
            callback=self.callback,
            complete_callback=self.complete_callback,
            argname_shorten=self.argname_shorten,
            **self._kwargs,
        )
        param.ns_param = self.ns_param
        return param

    def copy(self) -> "Param":
        """Copy a parameter so that it can be reused.

        Returns:
            The copy of the parameter
        """
        return self.__class__(
            names=self.names,
            default=self.default,
            desc=self.desc,
            prefix=self.prefix,
            show=self.show,
            required=self.required,
            subtype=self.subtype,
            callback=self.callback,
            type_frozen=self.type_frozen,
            complete_callback=self.complete_callback,
            argname_shorten=self.argname_shorten,
            **self._kwargs,
        )

    @property
    def default_group(self) -> str:
        """Get the default group of the parameter

        Returns:
            the default group name
        """
        ret: str = "REQUIRED OPTIONS" if self.required else "OPTIONAL OPTIONS"
        return (
            ret
            if not self.ns_param
            else f"{ret} UNDER {self.ns_param.name('long')}"
        )

    @property
    def desc_with_default(self) -> List[str]:
        """If default is not specified in desc, just to add with the default
        value

        Returns:
            list of descriptions with default value added
        """
        if self.is_help:
            return self.desc

        if self.required or (
            self.desc
            and any(
                "Default:" in desc or "DEFAULT:" in desc for desc in self.desc
            )
        ):
            return None if self.desc is None else self.desc[:]

        desc: List[str] = self.desc[:] if self.desc else [""]
        if desc[0] and not desc[0][-1:].isspace():
            desc[0] += " "

        default_str: str = str(self.default) or "''"
        desc[0] += f"Default: {default_str}"
        return desc

    def push(self, item: Any) -> None:
        """Push a value into the stack for calculating

        Returns:
            The item to be pushed
        """
        if self.hit is True and self._stack:
            logger.warning(
                "Previous value of argument %r is overwritten with %r.",
                self.namestr(),
                item,
            )
            self._stack = []

        if self.hit or not self._stack:
            self._stack.append([])
        self._stack[-1].append(item)
        self.hit = False

    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__}({self.namestr()} :: "
            f"{self.typestr()}) @ {id(self)}>"
        )

    def _value(self) -> Any:
        """Get the organized value of this parameter

        Returns:
            The parsed value of thie parameter
        """
        if not self._stack:
            if self.required:
                raise PyParamValueError("Argument is required.")
            return self.default
        ret = self._stack[-1][0]
        self._stack = []
        return ret

    @property
    def value(self) -> Any:
        """Return the cached value if possible, otherwise calcuate one

        Returns:
            The cached value of this parameter or the newly calculated
                from stack
        """
        if self._value_cached is not None:
            return self._value_cached
        self._value_cached = self._value()
        return self._value_cached

    def apply_callback(self, all_values: Namespace) -> Any:
        """Apply the callback function to the value

        Args:
            all_values: The namespace of values of all parameters

        Returns:
            The value after the callback applied

        Raises:
            PyParamTypeError: When exceptions raised or returned from callback
        """
        if not callable(self.callback):
            return self.value

        try:
            val = self.callback(self.value, all_values)
        except TypeError as terr:
            # len() takes exactly one argument (2 given)
            # <lambda>() takes 1 positional argument but 2 were given
            if not re.search(r"takes .+ argument .+ given", str(terr)):
                raise
            val = self.callback(self.value)

        if isinstance(val, Exception):
            raise PyParamTypeError(str(val))
        return val


class ParamAuto(Param):
    """An auto parameter whose value is automatically casted"""

    type: str = "auto"

    def _value(self) -> Any:
        """Cast value automatically"""
        return cast_to(super()._value(), "auto")


class ParamInt(Param):
    """An int parameter whose value is automatically casted into an int"""

    type: str = "int"
    type_aliases: List[str] = ["i"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # self.default = self.default or 0

    def _value(self) -> int:
        val = super()._value()
        try:
            return None if val is None else int(val)
        except ValueError as verr:
            raise PyParamValueError(str(verr)) from None


class ParamFloat(Param):
    """A float parameter whose value is automatically casted into a float"""

    type: str = "float"
    type_aliases: List[str] = ["f"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # self.default = self.default or 0.0

    def _value(self) -> float:
        val = super()._value()
        try:
            return None if val is None else float(val)
        except ValueError as verr:
            raise PyParamValueError(str(verr)) from None


class ParamStr(Param):
    """A str parameter whose value is automatically casted into a str"""

    type: str = "str"
    type_aliases: List[str] = ["s"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # self.default = self.default or ''


class ParamBool(Param):
    """A bool parameter whose value is automatically casted into a bool"""

    type: str = "bool"
    type_aliases: List[str] = ["b", "flag"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # self.default = self.default or False
        if self.default is not None:
            try:
                self.default = cast_to(str(self.default), "bool")
            except (PyParamValueError, PyParamTypeError):
                raise PyParamValueError(
                    "Default value of a count argument must be a bool value or "
                    "a value that can be casted to a bool value."
                ) from None

    def usagestr(self) -> str:
        """Get the string representation of the parameter in the default usage
        constructor

        Returns:
            the string representation of the parameter in the default usage
        """
        return self.name("long")

    def optstr(self) -> str:
        """Get the string representation of the parameter names and types
        in the optname section in help page

        Returns:
            the string representation of the parameter names and types
                in the optname section in help page
        """
        if self.is_help:
            return self.namestr()
        typestr: str = (
            self.typestr().upper() if self.type_frozen else self.typestr()
        )

        if not self.ns_param or not self.argname_shorten:
            # * makes sure it's not wrapped'
            return f"{self.namestr()}*[{typestr}]"

        ret: List[str] = []
        for term in sorted(self.terminals, key=len):
            ret.append(f"~<ns>.{term}")
        return ", ".join(ret) + f"*[{typestr}]"

    def close(self) -> None:
        if self.hit is True:
            self.push("true")

    def consume(self, value: str) -> bool:
        """Should I consume given value?"""
        if not self.hit:
            return False

        try:
            cast_to(value, "bool")
        except (PyParamValueError, PyParamTypeError):
            return False  # cannot cast, don't consume
        else:
            self.push(value)
            return True

    def _value(self) -> bool:
        if not self._stack:
            return self.default

        val = self._stack[-1][0]
        ret = None if val is None else cast_to(val, "bool")
        self._stack = []
        return ret

    def complete_value(
        self, current: str, prefix: str = ""
    ) -> Union[
        str,
        Iterator[Tuple[str]],
        Iterator[Tuple[str, str]],
        Iterator[Tuple[str, str, str]],
    ]:
        """Get the completion candidates for the current parameter"""
        if self.is_help:
            return ""
        if callable(self.complete_callback):
            return super().complete_value(current, prefix)
        if current:
            trues: List[str] = ("True", "true", "TRUE", "1")
            falses: List[str] = ("False", "false", "FALSE", "0")
            ret: List[Tuple[str, str, str]] = []
            for cand in trues:
                if cand.startswith(current):
                    ret.append((f"{prefix}{cand}", "plain", "Value True"))

            for cand in falses:
                if cand.startswith(current):
                    ret.append((f"{prefix}{cand}", "plain", "Value False"))
            return ret
        return ""


class ParamCount(Param):
    """A bool parameter whose value is automatically casted into a bool"""

    type: str = "count"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.default = self.default or 0
        if self.default is not None and self.default != 0:
            raise PyParamValueError(
                "Default value of a count argument must be 0"
            )

        if len(self.name("short", with_prefix=False)) != 1:
            raise PyParamValueError("Count argument must have a short name.")

        self._kwargs.setdefault("max", 0)  # 0: no max
        if not isinstance(self._kwargs["max"], int) or self._kwargs["max"] < 0:
            raise PyParamValueError(
                "Argument 'max' for count argument must be a positive integer"
            )

    def close(self) -> None:
        if self.hit is True:
            self.push("1")

    def consume(self, value: str) -> bool:
        """Should I consume given parameter?"""
        if self.hit and value.isdigit():
            self.push(value)
            return True
        return False

    def _value(self) -> int:
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
                "Expect repeated short names or "
                "an integer as count argument value."
            )
        if self._kwargs["max"] and retval > self._kwargs["max"]:
            raise PyParamValueError(
                f"{retval} is greater than "
                f"the max of {self._kwargs['max']}."
            )
        return retval

    def complete_name(self, current: str) -> Iterator[Tuple[str, str]]:
        """Complete names for a count parameter

        Since we have -v, -vv, -vvv allowed for a count parameter, we need
        to put them in the completions, too.
        """
        # check if current is trying to do so
        for name in self.names:
            if len(name) != 1:
                continue
            # current is not like -vvv
            if self._prefix_name(name) + len(current[2:]) * name != current:
                continue
            # check the max
            value: int = len(current) - 1
            if self._kwargs["max"] and value >= self._kwargs["max"]:
                # already max'ed, no further completion
                continue

            ncompletes: int = (
                min(self._kwargs["max"] - value, 2)
                if self._kwargs["max"]
                else 2
            )
            for i in range(ncompletes):
                yield current + name * (i + 1), self.desc[0].splitlines()[0]
            break

        else:
            yield from super().complete_name(current)


class ParamPath(Param):
    """A path parameter whose value is automatically casted into a pathlib.Path
    """

    type: str = "path"
    type_aliases: List[str] = ["p", "file"]

    def _value(self) -> Path:
        val: Path = super()._value()
        return None if val is None else Path(val)

    def complete_value(
        self, current: str, prefix: str = ""
    ) -> Union[str, Iterator[Tuple[str, ...]]]:
        """Generate file paths with given current prefix
        as completion candidates

        Args:
            current: The current word or prefix under cursor
        """
        if callable(self.complete_callback):
            return super().complete_value(current, prefix)
        return [(current, "file", prefix)]


class ParamDir(ParamPath):
    """Subclass of ParamPath.

    It does not make any difference with pyparam. However, it works differently
    for completions. The completion items for this param will only give
    directories instead of all paths
    """

    type: str = "dir"
    type_aliases: List[str] = []

    def complete_value(
        self, current: str, prefix: str = ""
    ) -> Union[str, Iterator[Tuple[str, ...]]]:
        """Generate dir paths with given current prefix as completion candidates

        Args:
            current: The current word or prefix under cursor
        """
        if callable(self.complete_callback):
            return super().complete_value(current, prefix)
        return [(current, "dir", prefix)]


class ParamPy(Param):
    """A parameter whose value will be ast.literal_eval'ed"""

    type: str = "py"

    def _value(self) -> Any:
        return ast.literal_eval(str(super()._value()))


class ParamJson(Param):
    """A parameter whose value will be parsed as json"""

    type: str = "json"
    type_aliases: List[str] = ["j"]

    def _value(self) -> Any:
        val: Any = super()._value()
        return None if val is None else json.loads(str(val))


class ParamList(Param):
    """A parameter whose value is a list"""

    type: str = "list"
    type_aliases: List[str] = ["l", "a", "array"]
    complete_relapse: bool = True

    @classmethod
    def on_register(cls):
        """Also register reset type"""
        name = "reset"
        aliases = ["r"]
        all_names = [name] + aliases

        for nam in all_names:
            TYPE_NAMES[nam] = name

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.default = self.default or []
        self._stack.append(self.default)

    def overwrite_type(self, param_type: str) -> "Param":
        """Deal with when param_type is reset"""
        if param_type == "reset":
            self._stack = []
            return self
        return super().overwrite_type(param_type)

    def consume(self, value: str) -> bool:
        """Should I consume given parameter?"""
        self.push(value)
        return True

    def push(self, item: str):
        """Push a value into the stack for calculating"""
        if self.hit or not self._stack:
            self._stack.append([])
        self._stack[-1].append(item)
        self.hit = False

    def _value(self) -> List[Any]:
        """Get the value a list parameter"""
        ret = [
            cast_to(val, self.subtype)
            for sublist in self._stack
            for val in sublist
        ]

        if self.required and not ret:
            raise PyParamValueError(ARGUMENT_REQUIRED)
        self._stack = []
        return ret


class ParamChoice(Param):
    """A bool parameter whose value is automatically casted into a bool"""

    type: str = "choice"
    type_aliases: List[str] = ["c"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if "choices" not in self._kwargs:
            raise PyParamValueError(
                "Argument 'choices' is required " "for ParamChoice."
            )

        if not isinstance(self._kwargs["choices"], (list, tuple)):
            raise PyParamValueError(
                "Argument 'choices' must be " "a list or a tuple."
            )

        # if not self.required and self.default is None:
        #     self.default = self._kwargs['choices'][0]

    def _value(self) -> Any:
        val = super()._value()

        if val is not None and val not in self._kwargs["choices"]:
            raise PyParamValueError(
                f"{val} is not one of {self._kwargs['choices']}"
            )
        self._stack = []
        return val

    def complete_value(
        self, current: str, prefix: str = ""
    ) -> Union[str, Iterator[Tuple[str, ...]]]:
        """Generate choices with given current prefix as completion candidates

        Args:
            current: The current word or prefix under cursor
        """
        if callable(self.complete_callback):
            return super().complete_value(current, prefix)

        ret: Iterator[Tuple[str]] = []
        for choice in self._kwargs["choices"]:
            if choice.startswith(current):
                ret.append((f"{prefix}{choice}",))
        return ret


class ParamNamespace(Param):
    """A pseudo parameter serving as a namespace for parameters under it

    So that it is possible to do:
    ```shell
    prog --namespace.arg1 1 --namespace.arg2 2
    ```
    """

    type: str = "ns"
    type_aliases: List[str] = ["namespace"]

    def __init__(self, *args, **kwargs):
        kwargs["desc"] = kwargs.get("desc") or [
            "Works as a namespace for other arguments.",
            "Never pass a value directly to it.",
        ]
        kwargs["default"] = None
        super().__init__(*args, **kwargs)
        self._stack = OrderedDiot()  # for my decendents

    @property
    def default_group(self) -> str:
        """Get the default group of the parameter"""
        ret: str = (
            "REQUIRED"
            if any(param.required for param in self._stack.values())
            else "OPTIONAL"
        )
        return (
            f"{ret} OPTIONS"
            if not self.ns_param
            else f'{ret} OPTIONS UNDER {self.ns_param.name("long")}'
        )

    @property
    def desc_with_default(self) -> List[str]:
        """Namespace parameters do not have a default value"""
        return self.desc[:]

    def decendents(self, show_only=False) -> List["Param"]:
        """Get all decendents of this namespace parameter

        Args:
            show_only: Load params with show=True only?

        Returns:
            The decendents of this namespace parameter
        """
        ret: List["Param"] = []
        ret_append: Callable = ret.append
        for param in self._stack.values():
            # don't skip entire ns parameter
            if isinstance(param, ParamNamespace):
                if (not show_only or param.show) and param not in ret:
                    ret.append(param)
                ret.extend(param.decendents(show_only))
                continue
            if show_only and not param.show:
                continue
            if param not in ret:
                ret_append(param)
        return ret

    def consume(self, value: str) -> bool:
        """Should I consume given parameter?"""
        return False

    def get_param(self, name: str, depth: int = 0) -> "Param":
        """Get the paraemeter by given name

        This parameter is like '-a', and the name can be 'a.b.c.d'

        Args:
            name: The name of the parameter to get
            depth: The depth

        Returns:
            The parameter we get with the given name
        """
        parts: List[str] = name.split(".")
        if depth < len(parts) - 1:
            part = parts[depth + 1]
            if part not in self._stack:
                return None
            if not isinstance(
                self._stack[part],  # type: ignore
                ParamNamespace,
            ):
                return self._stack[part]  # type: ignore
            return self._stack[part].get_param(name, depth + 1)  # type: ignore
        if name in self.names:
            return self
        return None

    def push(self, item: "Param", depth: int = 0) -> None:
        """Push the parameter under this namespace.

        We are not pushing any values to this namespace, but pushing
        parameters that are under it.
        """
        # check if item's namespaces at depth contain only names of this
        # ns parameter
        if set(item.namespaces(depth)) - set(self.terminals):  # type: ignore
            raise PyParamValueError(
                "Parameter names should only contain namespace names "
                "that belong to the same namespace parameter."
            )

        # set the names with all possible combination
        item._namespaces[depth] = self.terminals  # [:]
        item.full_names()

        # check if we have nested namespaces
        if 0 <= depth < item.namespaces("len") - 1:  # type: ignore
            # see if sub-ns exists
            subns_name = item.namespaces(depth + 1)[0]  # type: ignore
            if subns_name in self._stack:
                subns = self._stack[subns_name]  # type: ignore
            else:
                subns = ParamNamespace(
                    [
                        ".".join(prod)
                        for prod in product(
                            *(
                                item.namespaces(i)  # type: ignore
                                for i in range(depth + 2)
                            )
                        )
                    ]
                )
                subns.ns_param = self

                for name in subns.terminals:
                    self._stack[name] = subns
            subns.push(item, depth + 1)
        else:
            item.ns_param = self
            for term in item.terminals:
                self._stack[term] = item  # type: ignore

    def _value(self) -> Namespace:
        val = Namespace()
        for param_name, param in self._stack.items():
            if param_name not in val:
                for name in param.terminals:
                    val[name] = param.value
        return val

    def copy(self) -> "Param":
        """Copy a parameter so that it can be reused.

        Returns:
            The copy of the parameter
        """
        copied = super().copy()
        copied._stack = OrderedDiot(
            [(key, param.copy()) for key, param in self._stack.items()]
        )
        return copied

    def apply_callback(self, all_values: Namespace) -> Any:
        ns_callback_applied = Namespace()
        for param_name, param in self._stack.items():
            if param_name not in ns_callback_applied:
                for name in param.terminals:
                    ns_callback_applied[name] = param.apply_callback(
                        all_values
                    )

        if not callable(self.callback):
            return ns_callback_applied

        try:
            val = self.callback(ns_callback_applied, all_values)
        except TypeError as terr:
            # len() takes exactly one argument (2 given)
            # <lambda>() takes 1 positional argument but 2 were given
            if not re.search(r"takes .+ argument .+ given", str(terr)):
                raise
            val = self.callback(ns_callback_applied)

        if isinstance(val, Exception):
            raise PyParamTypeError(str(val))
        return val


def register_param(param: Type[Param]) -> None:
    """Register a parameter class

    Args:
        param: The param to register
            A param class should include a type
            You can also define type alias for a param type
    """
    for alias in param.type_aliases + [param.type]:
        if alias in TYPE_NAMES:
            raise PyParamNameError(
                "Type name has already been " f"registered: {alias}"
            )
        TYPE_NAMES[alias] = param.type

    PARAM_MAPPINGS[param.type] = param
    param.on_register()


for param_class in (
    ParamAuto,
    ParamInt,
    ParamStr,
    ParamFloat,
    ParamBool,
    ParamCount,
    ParamPath,
    ParamDir,
    ParamPy,
    ParamJson,
    ParamList,
    ParamChoice,
    ParamNamespace,
):
    register_param(param_class)
