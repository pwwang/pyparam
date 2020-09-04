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

POSITIONAL: str = ''

# - Single value types:
#     auto, int, str, float, bool, count, py, json
# - Complex value types:
#     list[<single/complex value type>], ns
TYPE_NAMES: Dict[str, str] = {}

CONSOLE_WIDTH: int = 80
# indention for each section
HELP_SECTION_INDENT: int = 2
# The width of the options in help
HELP_OPTION_WIDTH: int = 34
