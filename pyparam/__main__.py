"""For users to test arbitrary parsing"""
import logging
from rich import print # pylint: disable=redefined-builtin
from . import Params
from .utils import logger

def main():
    """Main entry"""
    params = Params(
        prog='python -m pyparam',
        desc=("An expo showing all supported types of parameters "
              "and some features."),
    )
    params.add_param('d,debug', False,
                     desc='Show the debug logging of the parsing process?')
    predefined = params.add_command("p, pred, pd, pdf, predef, predefined, "
                                  "pre-defined, pre-defined-args",
                                  "Some predefined arguments.")


    params.add_command("arbi, arbitrary",
                       desc="No predefined arguments, but you can "
                       "pass arbitrary arguments and see how "
                       "`pyparam` parses them",
                       arbitrary=True)

    fromfile = params.add_command(
        "fromfile", desc=[
            "Load parameter definition from file.",
            "You can load parameter definitions from any file type that "
            "`python-simpleconf` supports."
            "For example, a toml file:",
            "",
            "```toml",
            "[params.arg]",
            "desc = \"An argument\"",
            "```",
            "",
        ]
    )

    parsed = params.parse()

    if not parsed:
        logger.warning("Pass some arguments to show the results.")
        return

    if parsed.debug:
        logger.setLevel(logging.DEBUG)
        params.parse()

    print()
    print("Arguments passed in:")
    print()
    print(parsed)

if __name__ == "__main__":
    main()
