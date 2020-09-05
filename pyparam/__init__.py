"""
parameters module for PyPPL
"""

__version__ = "0.2.6"

from .params import Param, Params
from .commands import Commands

# pylint: disable=invalid-name
params = Params()
commands = Commands()
