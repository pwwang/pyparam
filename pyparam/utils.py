"""Utilities for pyparam

Attributes:
    logger: The logger
"""
import ast
import builtins
import json
import logging
from argparse import Namespace as APNamespace
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple, Type, Union

from rich.console import Console
from rich.logging import RichHandler as _RichHandler
from rich.padding import Padding
from rich.syntax import Syntax
from rich.text import Text

from .defaults import TYPE_NAMES
from .exceptions import PyParamTypeError


class Namespace(APNamespace):
    """Subclass of `argparse.Namespace`

    We have enabled `__getitem__`, `__setitem__`, `__len__` and `__contains__`.
    So that you can do:

    ```python
    ns = Namespace()
    ns['a'] = 1  # same as ns.a = 1
    ns['a'] == 1 # same as ns.a == 1
    len(ns) == 1
    'a' in ns
    ```

    Attributes:
        __command__: The command name if matched.
    """

    __command__: str = None

    def __getitem__(self, name: str) -> Any:
        return getattr(self, name)

    def __setitem__(self, name: str, value: Any) -> None:
        setattr(self, name, value)

    def __len__(self) -> int:
        return len(vars(self))

    def __contains__(self, name: str) -> bool:
        return name in vars(self)

    def __or__(self, other):
        # copy myself
        myself: Namespace = self.__class__()
        myself |= self
        myself |= other
        return myself

    def __ior__(self, other):
        if not isinstance(other, dict):
            other = vars(other)
        for key, value in other.items():
            self[key] = value
        return self

    def _to_dict(self, dict_wrapper: Type = None) -> Dict:
        """Convert the namespace to a dict object"""
        out = {}
        for key in vars(self):
            out[key] = self[key]
        if not dict_wrapper:
            return out
        return dict_wrapper(out)


class Codeblock:
    """A code block, will be rendered as rich.syntax.Syntax"""

    @classmethod
    def scan_texts(
        cls, texts: List[str], check_default: bool = False
    ) -> List[Union[str, "Codeblock"]]:
        """Scan multiple texts for code blocks

        Args:
            cls (Codeblock class): The class
            texts: a list of texts
            check_default: Check if there is default in maybe_codeblock.
                Defaults should not be scanned as code blocks

        Returns:
            mixed text and code blocks
        """

        ret: List[Union[str, "Codeblock"]] = []
        ret_extend: Callable = ret.extend
        codeblock: "Codeblock" = None
        # Type: Union[str, Codeblock]
        for text in texts:
            if not codeblock:
                if not text:
                    ret.append(text)
                    continue
                scanned, codeblock = cls.scan(
                    text, check_default=check_default
                )
                ret_extend(scanned)
                continue
            # if we hit an unclosed codeblock
            lines: List[str] = text.splitlines()
            # Type: int, str
            for i, line in enumerate(lines):
                if codeblock.is_end(line):
                    scanned, codeblock = cls.scan(
                        "\n".join(
                            lines[
                                (i if codeblock.opentag == ">>>" else i + 1) :
                            ]
                        ),
                        check_default=check_default,
                    )
                    ret_extend(scanned)
                    break
            else:
                codeblock.add_code(text)
        return ret

    @classmethod
    def scan(
        cls, maybe_codeblock: str, check_default: bool = False
    ) -> Tuple[List[Union[str, "Codeblock"]], "Codeblock"]:
        """Scan and try to create codeblock objects from maybe_codeblock

        Args:
            cls (Codeblock class): The class
            maybe_codeblock: Maybe a code block start
                It can be a text block, we have to scan if it has code blocks
                inside.
            check_default: Check if there is default in maybe_codeblock.
                Defaults should not be scanned as code blocks

        Returns:
            mixed text and unclosed code blocks
        """
        sep: str = (
            "Default:"
            if "Default:" in maybe_codeblock
            else "DEFAULT:"
            if "DEFAULT:" in maybe_codeblock
            else None
        )

        default_to_append: str = None
        default_in_newline = False
        if check_default and sep:
            parts: List[str] = maybe_codeblock.split(sep, 1)
            default_to_append = sep + parts[1]
            default_in_newline = parts[0].endswith("\n")
            lines: List[str] = parts[0].splitlines()
        else:
            lines: List[str] = maybe_codeblock.splitlines()

        ret: List[Union[str, "Codeblock"]] = []
        ret_append: Callable = ret.append
        codeblock: "Codeblock" = None
        # Type: str
        for line in lines:
            if not codeblock:
                line_lstripped: str = line.lstrip()
                if line_lstripped.startswith(">>>"):
                    codeblock: "Codeblock" = cls(
                        ">>>",
                        "pycon",
                        len(line) - len(line_lstripped),
                        [line_lstripped],
                    )
                    ret_append(codeblock)
                elif line_lstripped.startswith("```"):
                    codeblock: "Codeblock" = cls(
                        line_lstripped[
                            : (
                                len(line_lstripped)
                                - len(line_lstripped.lstrip("`"))
                            )
                        ],
                        line_lstripped.lstrip("`").strip() or "text",
                        len(line) - len(line_lstripped),
                    )
                    ret_append(codeblock)
                else:
                    ret_append(line)
            elif codeblock.is_end(line):
                if codeblock.opentag == ">>>":
                    ret.append(line)
                codeblock = None
            else:
                codeblock.add_code(line)

        if default_to_append:
            # if codeblock (>>>) is not closed.
            # but we have default so it actually closes
            if codeblock and codeblock.opentag == ">>>":
                codeblock = None
            if not ret or isinstance(ret[-1], Codeblock) or default_in_newline:
                ret.append(default_to_append)
            else:
                ret[-1] += default_to_append
        return ret, codeblock

    def __init__(
        self,
        opentag: str,
        lang: str,
        indent: int,
        codes: List[str] = None,
    ) -> None:
        """Constructor

        Args:
            opentag: The opentag for the code block.
                One of '>>>', '```<lang>', '````<lang>', ...
            lang: The language name
            indent: The indentation level
            codes: The lines of code
        """
        self.opentag: str = opentag
        self.lang: str = lang
        self.indent: int = indent
        self.codes: List[str] = codes or []

    def __repr__(self) -> str:
        return (
            f"<Codeblock (tag={self.opentag}, lang={self.lang}, "
            f"codes={self.codes[:1]} ...)"
        )

    def add_code(self, code: str) -> None:
        """Add code to code block

        Args:
            code: code to add
                It can be multiple lines, each of which will be dedented
        """
        # Type: str
        for line in code.splitlines():
            self.codes.append(line[self.indent :])

    def is_end(self, line: str) -> bool:
        """Tell if the line is the end of the code block

        Args:
            line: line to check

        Returns:
            True if it is the end otherwise False
        """
        if self.opentag == ">>>" and not line[self.indent :].startswith(">>>"):
            return True
        if (
            "`" in self.opentag
            and line[self.indent :].rstrip() == self.opentag
        ):
            return True
        return False

    def render(self) -> Padding:
        """Render the code block to a rich.syntax.Syntax

        Returns:
            A padding of rich.syntax.Syntax
        """
        return Padding(
            Syntax("\n".join(self.codes), self.lang), (0, 0, 0, self.indent)
        )


def always_list(
    str_or_list: Union[str, List[str]],
    strip: bool = True,
    split: Union[str, bool] = ",",
) -> List[str]:
    """Convert a string (comma separated) or a list to a list

    Args:
        str_or_list: string or list
        strip: whether to strip the elements in result list
        split: Delimiter for split or False to not split

    Return:
        list: list of strings
    """
    if isinstance(str_or_list, (list, tuple)):
        return list(str_or_list)
    if split:
        return [
            elem.strip() if strip else elem
            for elem in str_or_list.split(split)  # type: ignore
        ]
    return [str_or_list]


def parse_type(typestr: str) -> List[str]:
    """Parse the type string

    Examples:
        >>> parse_type(None)    # None, None
        >>> parse_type("array") # list, None
        >>> parse_type("a:i")   # list, int
        >>> parse_type("j")     # json, None
        >>> parse_type("list")  # list, None

    Args:
        typestr: string of type to parse

    Returns:
        Main type and subtype

    Raises:
        PyParamTypeError: When a type cannot be parsed
    """
    if typestr is None:
        return [None, None]

    parts: List[str] = typestr.split(":", 1)
    # Type: int, str
    for i, part in enumerate(parts):
        if part not in TYPE_NAMES:
            raise PyParamTypeError("Unknown type: %s" % typestr)
        parts[i] = TYPE_NAMES[part]

    parts.append(None)
    return parts[:2]


@lru_cache()
def parse_potential_argument(
    arg: str, prefix: str, allow_attached: bool = False
) -> Tuple[str, str, str]:
    """Parse a potential argument with given prefix

    Examples:
        >>> # prefix == 'auto
        >>> parse_potential_argument("-a")     # a, None, None
        >>> parse_potential_argument("--arg")  # arg, None, None
        >>> parse_potential_argument("--a")    # None, None, a
        >>> parse_potential_argument("-abc")   # None, None, -abc
        >>> parse_potential_argument("-abc", allow_attached=True)
        >>> # -a, None, bc

    Args:
        arg: a potential argument. Such as:
            -a, --def, -b=1, --abc=value, -b1 (for argument -b with value 1)
            with types:
            -a:int --def:list -b:str=1 --abs:str=value -b:bool
            It is usually one element of the sys.argv
        prefix: The prefix for the argument names
        allow_attached: Whether to detect item like '-b1' for argument
            '-b' with value '1' or the entire one is parsed as argument '-b1'

    Returns:
        The argument name, type and value
            When arg cannot be parsed as an argument, argument name and type
            will both be None. arg will be returned as argument value.
    """
    if not arg.startswith("-" if prefix == "auto" else prefix):
        return None, None, arg

    # fill a tuple to length of 2 with None
    fill2_none: Callable = lambda alist: (
        (alist[0], None) if len(alist) == 1 or not alist[1] else alist[:2]
    )

    item_nametype, item_value = fill2_none(arg.split("=", 1))
    item_name, item_type = fill2_none(item_nametype.split(":", 1))

    # detach the value for -b1
    if allow_attached:
        single_prefix: str = "-" if prefix == "auto" else prefix
        len_spref: int = len(single_prefix)
        if (
            item_type is None
            and item_value is None
            and (
                item_name.startswith(single_prefix)
                and item_name[len_spref : len_spref + 1] != single_prefix
            )
        ):
            # Type: str, str
            item_name, item_value = (
                single_prefix + item_name[len_spref : len_spref + 1],
                item_name[len_spref + 1 :],
            )

    # remove prefix in item_name
    if prefix == "auto":
        item_name_first: str = item_name.split(".")[0]
        prefix = (
            "-"
            if len(item_name_first) <= 2
            else "--"
            if len(item_name_first) >= 4
            else None
        )

    if prefix is not None and item_name.startswith(prefix):
        item_name = item_name[len(prefix) :]
    else:
        return None, None, arg

    item_type, item_subtype = parse_type(item_type)
    item_type = f"{item_type}:{item_subtype}" if item_subtype else item_type

    return item_name, item_type, item_value


def type_from_value(value: Any) -> str:
    """Detect parameter type from a value

    Args:
        value: The value

    Returns:
        The name of the type

    Raises:
        PyParamTypeError: When we have list as subtype.
            For example, when value is `[[1]]`
    """
    typename: str = type(value).__name__
    if typename in ("int", "float", "str", "bool"):
        return typename
    if isinstance(value, list):
        if not value:
            return "list"
        type0: str = type_from_value(value[0])
        if "list" in type0:
            raise PyParamTypeError("Cannot have 'list' as subtype.")
        return (
            f"list:{type0}"
            if all(type_from_value(item) == type0 for item in value[1:])
            else "list"
        )
    if isinstance(value, dict):
        return "json"
    if isinstance(value, Path):
        return "path"
    return "auto"


def _cast_auto(value: Any) -> Any:
    """Cast value automatically

    Args:
        value: value to cast

    Returns:
        value casted
    """
    if value in ("True", "TRUE", "true") or value is True:
        return True
    if value in ("False", "FALSE", "false") or value is False:
        return False

    try:
        return int(value)
    except (TypeError, ValueError):
        pass

    try:
        return float(value)
    except (TypeError, ValueError):
        pass

    try:
        return json.loads(value)
    except (TypeError, ValueError, json.JSONDecodeError):
        pass

    return value


def cast_to(value: Any, to_type: Union[str, bool]) -> Any:
    """Cast a value to a given type

    Args:
        value: value to cast
        to_type: type to cast

    Returns:
        casted value

    Raises:
        PyParamTypeError: if value is not able to be casted
    """
    try:
        if to_type in ("int", "float", "str"):
            return getattr(builtins, to_type)(value)  # type: ignore
        if to_type == "bool":
            if value in ("true", "TRUE", "True", "1", 1, True):
                return True
            if value in ("false", "FALSE", "False", "0", 0, False):
                return False
            raise PyParamTypeError(
                "Expecting one of [true, TRUE, True, 1, false, FALSE, False, 0]"
            )

        if to_type in ("path", "py", "json"):
            return {"path": Path, "py": ast.literal_eval, "json": json.loads}[
                to_type  # type: ignore
            ](str(value))
        if to_type in (None, "auto"):
            return _cast_auto(value)
    except (TypeError, ValueError, json.JSONDecodeError) as cast_exc:
        raise PyParamTypeError(
            f"Cannot cast {value} to {to_type}: {cast_exc}"
        ) from cast_exc
    raise PyParamTypeError(f"Cannot cast {value} to {to_type}")


class RichHandler(_RichHandler):
    """Subclass of rich.logging.RichHandler, showing log levels as a single
    character"""

    def get_level_text(self, record: logging.LogRecord) -> Text:
        """Get the level name from the record.
        Args:
            record (LogRecord): LogRecord instance.
        Returns:
            Text: A tuple of the style and level name.
        """
        level_name = record.levelname
        level_text = Text.styled(
            level_name.upper() + ":", f"logging.level.{level_name.lower()}"
        )
        return level_text


logger = logging.getLogger(__name__)
logger.addHandler(
    RichHandler(
        logging.INFO, console=Console(), show_time=False, show_path=False
    )
)
