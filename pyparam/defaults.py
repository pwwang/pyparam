"""Defaults for pyparam"""
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
