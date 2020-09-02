"""Utilities for pyparam"""
import logging
import ast
import json
import builtins
from typing import (
    Any,
    List,
    Union,
    Callable,
    Optional,
    Tuple
)
from functools import lru_cache
from argparse import Namespace as APNamespace
from pathlib import Path
from rich.logging import RichHandler
from rich.padding import Padding
from rich.syntax import Syntax
from .defaults import TYPE_NAMES
from .exceptions import PyParamTypeError

class Namespace(APNamespace):
    """Subclass of argparse.Namespace with __getitem__ avaiable"""
    __command__ = None

    def __getitem__(self, name: str) -> Any:
        return getattr(self, name)

    def __setitem__(self, name: str, value: Any) -> None:
        setattr(self, name, value)

    def __len__(self) -> int:
        return len(vars(self))

    def __contains__(self, name: str) -> bool:
        return hasattr(self, name)

class Codeblock:
    """A code block, will be rendered as rich.syntax.Syntax"""

    @classmethod
    def scan_texts(
        cls,
        texts:
        List[str],
        check_default: bool = False
    ) -> List[Union[str, 'Codeblock']]:
        """Scan multiple texts for code blocks

        Args:
            cls (Codeblock class): The class
            texts (list): a list of texts
            check_default (bool): Check if there is default in maybe_codeblock.
                Defaults should not be scanned as code blocks

        Returns:
            list: mixed text and code blocks
        """

        ret: List[Union[str, 'Codeblock']] = []
        ret_extend: Callable = ret.extend
        codeblock: Optional['Codeblock'] = None
        # Type: Union[str, Codeblock]
        for text in texts:
            if not codeblock:
                if not text:
                    ret.append(text)
                    continue
                # Type: List[Union[str, Codeblock]], Optional[Codeblock]
                scanned, codeblock = cls.scan(text, check_default=check_default)
                ret_extend(scanned)
                continue
            # if we hit an unclosed codeblock
            lines: List[str] = text.splitlines()
            # Type: int, str
            for i, line in enumerate(lines):
                if codeblock.is_end(line):
                    # Type: List[Union[str, Codeblock]], Optional[Codeblock]
                    scanned, codeblock = cls.scan(
                        '\n'.join(
                            lines[(i if codeblock.opentag == '>>>' else i+1):]
                        ),
                        check_default=check_default
                    )
                    ret_extend(scanned)
                    break
            else:
                codeblock.add_code(text)
        return ret

    @classmethod
    def scan(
        cls,
        maybe_codeblock: str,
        check_default: bool = False
    ) -> Tuple[List[Union[str, 'Codeblock']], Optional['Codeblock']]:
        """Scan and try to create codeblock objects from maybe_codeblock

        Args:
            cls (Codeblock class): The class
            maybe_codeblock (str): Maybe a code block start
                It can be a text block, we have to scan if it has code blocks
                inside.
            check_default (bool): Check if there is default in maybe_codeblock.
                Defaults should not be scanned as code blocks

        Returns:
            tuple (list, Codeblock): mixed text and unclosed code blocks
        """
        sep: Optional[str] = (
            'Default:' if 'Default:' in maybe_codeblock
            else 'DEFAULT:' if 'DEFAULT:' in maybe_codeblock
            else None
        )

        default_to_append: Optional[str] = None
        if check_default and sep:
            parts: List[str] = maybe_codeblock.split(sep, 1)
            default_to_append = sep + parts[1]
            lines: List[str] = parts[0].splitlines()
        else:
            lines: List[str] = maybe_codeblock.splitlines()

        ret: List[Union[str, 'Codeblock']] = []
        ret_append: Callable = ret.append
        codeblock: Optional['Codeblock'] = None
        # Type: str
        for line in lines:
            if not codeblock:
                line_lstripped: str = line.lstrip()
                if line_lstripped.startswith('>>>'):
                    codeblock: 'Codeblock' = cls(
                        '>>>',
                        'pycon',
                        len(line) - len(line_lstripped),
                        [line_lstripped]
                    )
                    ret_append(codeblock)
                elif line_lstripped.startswith('```'):
                    codeblock: 'Codeblock' = cls(
                        line_lstripped[
                            :(len(line_lstripped) -
                            len(line_lstripped.lstrip('`')))
                        ],
                        line_lstripped.lstrip('`').strip() or 'text',
                        len(line) - len(line_lstripped)
                    )
                    ret_append(codeblock)
                else:
                    ret_append(line)
            elif codeblock.is_end(line):
                if codeblock.opentag == '>>>':
                    ret.append(line)
                codeblock = None
            else:
                codeblock.add_code(line)

        if default_to_append:
            if not ret or isinstance(ret[-1], Codeblock):
                ret.append(default_to_append)
            else:
                ret[-1] += default_to_append
        return ret, codeblock

    def __init__(self,
                 opentag: str,
                 lang: str,
                 indent: int,
                 codes: Optional[List[str]] = None) -> None:
        """Constructor

        Args:
            opentag (str): The opentag for the code block.
                One of '>>>', '```<lang>', '````<lang>', ...
            lang (str): The language name
            indent (int): The indentation level
            codes (list): The lines of code
        """
        self.opentag: str = opentag
        self.lang: str = lang
        self.indent: int = indent
        self.codes: List[str] = codes or []

    def __repr__(self) -> str:
        return (f"<Codeblock (tag={self.opentag}, lang={self.lang}, "
                f"codes={self.codes[:1]} ...)")

    def add_code(self, code: str) -> None:
        """Add code to code block

        Args:
            code (str): code to add
                It can be multiple lines, each of which will be dedented
        """
        # Type: str
        for line in code.splitlines():
            self.codes.append(line[self.indent:])

    def is_end(self, line: str) -> bool:
        """Tell if the line is the end of the code block

        Args:
            line (str): line to check

        Returns:
            bool: True if it is the end otherwise False
        """
        if self.opentag == '>>>' and not line[self.indent:].startswith('>>>'):
            return True
        if '`' in self.opentag and line[self.indent:].rstrip() == self.opentag:
            return True
        return False

    def render(self) -> Padding:
        """Render the code block to a rich.syntax.Syntax

        Returns:
            Padding: A padding of rich.syntax.Syntax
        """
        return Padding(
            Syntax('\n'.join(self.codes), self.lang),
            (0, 0, 0, self.indent)
        )

def always_list(str_or_list: Union[str, List[str]],
                strip: bool = True,
                split: Union[str, bool] = ',') -> List[str]:
    """Convert a string (comma separated) or a list to a list

    Args:
        str_or_list (str|list): string or list
        strip (bool): whether to strip the elements in result list
        split (bool|str): Delimiter for split or False to not split

    Return:
        list: list of strings
    """
    if isinstance(str_or_list, (list, tuple)):
        return list(str_or_list)
    if split:
        return [elem.strip() if strip else elem
                for elem in str_or_list.split(split)]
    return [str_or_list]

def parse_type(typestr: str) -> List[Optional[str]]:
    """Parse the type string

    Examples:
        >>> parse_type(None)    # None, None
        >>> parse_type("array") # list, None
        >>> parse_type("a:i")   # list, int
        >>> parse_type("j")     # json, None
        >>> parse_type("list")  # list, None

    Args:
        typestr (str): string of type to parse

    Returns:
        list: Main type and subtype

    Raises:
        PyParamTypeError: When a type cannot be parsed
    """
    if typestr is None:
        return [None, None]

    parts: List[str] = typestr.split(':', 1)
    # Type: int, str
    for i, part in enumerate(parts):
        if part not in TYPE_NAMES:
            raise PyParamTypeError("Unknown type: %s" % typestr)
        parts[i] = TYPE_NAMES[part]

    parts.append(None)
    return parts[:2]

@lru_cache()
def parse_potential_argument(
    arg: str,
    prefix: str,
    allow_attached: bool = False
) -> Tuple[Optional[str], Optional[str], Optional[str]]:
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
        arg (str): a potential argument. Such as:
            -a, --def, -b=1, --abc=value, -b1 (for argument -b with value 1)
            with types:
            -a:int --def:list -b:str=1 --abs:str=value -b:bool
            It is usually one element of the sys.argv
        prefix (str): The prefix for the argument names
        allow_attached (bool): Whether to detect item like '-b1' for argument
            '-b' with value '1' or the entire one is parsed as argument '-b1'

    Returns:
        tuple (str, str, str): the argument name, type and value
            When arg cannot be parsed as an argument, argument name and type
            will both be None. arg will be returned as argument value.
    """
    if not arg.startswith('-' if prefix == 'auto' else prefix):
        return None, None, arg

    # fill a tuple to length of 2 with None
    fill2_none: Callable = lambda alist: (
        (alist[0], None) if len(alist) == 1 or not alist[1] else alist[:2]
    )

    # Type: str, Optional[str]
    item_nametype, item_value = fill2_none(arg.split('=', 1))
    # Type: str, Optional[str]
    item_name, item_type = fill2_none(item_nametype.split(':', 1))

    # detach the value for -b1
    if allow_attached:
        # pylint: disable=too-many-boolean-expressions
        if (item_type is None and item_value is None and (
            (prefix == 'auto' and item_name[:1] == '-' and
             item_name[:2] != '--') or
            (len(prefix) == 1 and
             item_name[1:2] != prefix )
        )):
            # Type: str, str
            item_name, item_value = item_name[:2], item_name[2:]

    # remove prefix in item_name
    if prefix == 'auto':
        item_name_first: str = item_name.split('.')[0]
        prefix = ('-' if len(item_name_first) <= 2
                  else '--' if len(item_name_first) >= 4
                  else None)

    if prefix and item_name.startswith(prefix):
        item_name = item_name[len(prefix):]
    else:
        return None, None, arg

    # Type: str, Optional[str]
    item_type, item_subtype = parse_type(item_type)
    item_type = f"{item_type}:{item_subtype}" if item_subtype else item_type

    return item_name, item_type, item_value

def type_from_value(value: Any) -> str:
    """Detect parameter type from a value

    Args:
        value (any): The value

    Returns:
        str: The name of the type
    """
    typename: str = type(value).__name__
    if typename in ('int', 'float', 'str', 'bool', 'list'):
        return typename
    if isinstance(value, dict):
        return 'json'
    if isinstance(value, Path):
        return 'path'
    return 'auto'

def _cast_auto(value: Any) -> Any:
    """Cast value automatically

    Args:
        value (any): value to cast

    Returns:
        any: value casted
    """
    # pylint: disable=too-many-return-statements
    if value in ("True", "TRUE", "true", 1, True):
        return True
    if value in ("False", "FALSE", "false", 0, False):
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

def cast_to(value: Any, to_type: str) -> Any:
    """Cast a value to a given type

    Args:
        value (any): value to cast
        to_type (str): type to cast

    Returns:
        any: casted value

    Raises:
        PyParamTypeError: if value is not able to be casted
    """
    try:
        if to_type in ('int', 'float', 'str'):
            return getattr(builtins, to_type)(value)
        if to_type == 'bool':
            if value in ('true', 'TRUE', 'True', '1', 1, True):
                return True
            if value in ('false', 'FALSE', 'False', '0', 0, False):
                return False
            raise ValueError(
                'Expecting one of [true, TRUE, True, 1, false, FALSE, False, 0]'
            )
        if to_type == 'path':
            return Path(value)
        if to_type == 'py':
            return ast.literal_eval(str(value))
        if to_type == 'json':
            return json.loads(str(value))
        if to_type in (None, 'auto'):
            return _cast_auto(value)
    except (TypeError, ValueError, json.JSONDecodeError) as cast_exc:
        raise PyParamTypeError(
            f"Cannot cast {value} to {to_type}: {cast_exc}"
        ) from cast_exc
    raise PyParamTypeError(f"Cannot cast {value} to {to_type}")

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(RichHandler(show_time=False, show_path=False))
