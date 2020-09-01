"""For users to test arbitrary parsing"""
import logging
from rich import print # pylint: disable=redefined-builtin
from . import Params, Namespace
from .utils import logger

def vars_ns(ns, depth=None):
    """Get the vars of a namespace"""
    ret = vars(ns)
    for key, val in ret.items():
        if (depth is None or depth > 0) and isinstance(val, Namespace):
            ret[key] = vars_ns(val, None if depth is None else depth - 1)
    return ret



def main():
    """Main entry"""
    params = Params(
        prog='python -m pyparam',
        desc=["An exhibition showing all supported types of parameters "
              "and some features by running {prog}.",
              "",
              "```python",
              "# We can also insert code block in the description.",
              "print('Hello pyparam!')",
              "```",
              "",
              ">>> # This is another example of code block "
              "using python console",
              ">>> print('Hello pyparam!')"
             ]
    )
    params.add_param('d,debug', False,
                     desc='Show the debug logging of the parsing process?')
    predefined = params.add_command("p, pred, pd, pdf, predef, predefined, "
                                  "pre-defined, pre-defined-args",
                                  "Some predefined arguments.")
    predefined.add_param('i, int', required=True, type=int, desc=[
        "An argument whose value will be casted into an integer.",
        "You can also try the short name with attached value: `-i1`"
    ])
    predefined.add_param('b, bool', type=bool, desc=[
        "A boolean/flag argument. ",
        "If it is hit by itself, `True` will be used. However, it can consume "
        "one of following values: [true, TRUE, True, 1, false, FALSE, False, 0]"
    ])

    params.add_command("a, arbi, arbitrary",
                       desc="No predefined arguments, but you can "
                       "pass arbitrary arguments and see how "
                       "`pyparam` parses them",
                       arbitrary=True)

    fromfile = params.add_command(
        "f, fromfile", desc=[
            "Load parameter definition from file.",
            "You can load parameter definitions from any file type that "
            "`python-simpleconf` supports. "
            "For example, a toml file:",
            "",
            "```toml",
            "[params.arg]",
            "desc = \"An argument\"",
            "```",
        ]
    )

    parsed = params.parse()

    if parsed.debug:
        logger.setLevel(logging.DEBUG)
        params.parse()

    print()
    print("Arguments passed in:")
    print()
    print(vars_ns(parsed))

if __name__ == "__main__":
    main()
