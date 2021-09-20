"""Defaults for pyparam

Holds some default values for pyparam.
To change any of the CONSOLE_WIDTH, HELP_SECTION_INDENT or HELP_OPTION_WIDTH:
```python
from pyparam import defaults
default.CONSOLE_WIDTH = 100
```

Attributes:
    POSITIONAL: The name of positional parameter
    TYPE_NAMES: The type name mappings to get the type name from aliases
        Do not modify this variable. It is maintained by
        `pyparam.param.regiest_param`
    CONSOLE_WIDTH: The total width for the help page.
    HELP_SECTION_INDENT: The indentation for the contents in a section
    HELP_OPTION_WIDTH: The width that the option name and type take up in
        the help page.
"""
from typing import Dict

from diot import Diot

POSITIONAL: str = ""

# - Single value types:
#     auto, int, str, float, bool, count, py, json
# - Complex value types:
#     list[<single/complex value type>], ns
TYPE_NAMES: Dict[str, str] = {}

CONSOLE_WIDTH: int = 80
# indention for the contents of each section
HELP_SECTION_INDENT: int = 2
# The width of the options in help
HELP_OPTION_WIDTH: int = 34

ARGUMENT_REQUIRED = "Argument is required."

# Default attribute values for a Params object
# This, as well as default attribute values for Param object,
# are useful to reduce the size of a dumped file
PARAMS: Diot = Diot(
    desc=["Not described."],
    help_keys=["h", "help"],
    help_cmds=["help"],
    help_on_void=True,
    prefix="auto",
    theme="default",
    usage=None,
    arbitrary=False,
)

PARAM: Diot = Diot(
    type=None,
    desc=["Not described."],
    default=None,
    show=True,
    type_frozen=True,
    argname_shorten=True,
    required=False,
)
