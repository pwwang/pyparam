"""For users to test arbitrary parsing"""
import logging
from rich import print # pylint: disable=redefined-builtin
from .. import Params
from ..utils import logger

def main():
    """Main entry"""
    params = Params(
        prog='python -m pyparam.arbi',
        desc=[
            "Testing arbitrary argument parsing with {prog}. ",
            "",
            "You can pass arbitrary arguments and see how pyparam parses them.",
            "You may also set the logging level to debug to see the process "
            "how pyparam parses them"],
        arbitrary=True,
        usage=[
            "{prog} [OPTIONS]",
            "{prog} debug [OPTIONS]",
        ]
    )
    params.add_command("debug", "Show debug logging for argument parsing.",
                       usage="{prog} debug [OPTIONS]")
    parsed = params.parse()

    if not parsed:
        logger.warning("Pass some arguments to show the results.")
        return

    if parsed.__command__ == 'debug':
        logger.setLevel(logging.DEBUG)
        parsed = params.parse()

    print()
    print("Arguments passed in:")
    print()
    print(parsed)

if __name__ == "__main__":
    main()
