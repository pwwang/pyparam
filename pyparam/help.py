"""Help assembler for pyparam"""
import re
import textwrap
from typing import (
    Dict,
    List,
    Optional,
    Type,
    Union,
    Callable,
    Tuple
)
from diot import OrderedDiot, Diot
from rich import box
from rich.table import Table
from rich.columns import Columns
from rich.padding import Padding
from rich.console import Console, RenderResult
from rich.theme import Theme
from rich.text import Text
from rich.highlighter import RegexHighlighter
from . import defaults
from .utils import Codeblock

THEMES: Dict[str, Theme] = dict(
    default=Theme(dict(
        title="bold cyan",
        prog="bold green",
        default="magenta",
        optname="bright_green",
        opttype="blue italic",
        opttype_frozen="blue"
    )),
)

# pylint: disable=too-few-public-methods
class ProgHighlighter(RegexHighlighter):
    """Apply style to anything that looks like a program name."""

    def __init__(self, prog: str):
        super().__init__()
        prog = re.escape(prog)
        self.highlights = [rf"(?P<prog>\b{prog}\b)"]

class OptnameHighlighter(RegexHighlighter):
    """Apply style to anything that looks like a option name.

    Highlight `-b` and `--box` in `-b, --box <INT>`, and all in commands:
    `i, install`
    """

    highlights: List[str] = [r"(?P<optname>[^\[<][^,\s]+)"]

class OpttypeHighlighter(RegexHighlighter):
    """Apply style to anything that looks like a option type."""

    highlights: List[str] = [
        r"(?P<opttype_frozen>[\[\<][A-Z:]+[\]\>])$",
        r"(?P<opttype>[\[\<][a-z:]+[\]\>])$",
    ]

class DefaultHighlighter(RegexHighlighter):
    """Apply style to anything that looks like default value in option desc."""

    highlights: List[str] = [r"(?P<default>D(?:efault|EFAULT):.+$)"]

class HelpSection(list):
    """Base class for all help sections."""

    def _highlight( # pylint: disable=no-self-use
            self,
            string: str,
            highlighters: Optional[List[Type[RegexHighlighter]]] = None
    ) -> Union[Text, str]:
        """Highlight the string using given highlighters"""
        if not highlighters:
            return string
        if not isinstance(highlighters, (tuple, list)):
            highlighters = [highlighters]
        for highlighter in highlighters:
            string = highlighter(string)

        return string

    def __rich_console__(self, console: Console, _) -> RenderResult:
        """Implement API from rich to print the help page"""
        scanned = Codeblock.scan_texts(self)
        for item in scanned:
            if isinstance(item, Codeblock):
                yield Padding(item.render(), (0, 0, 0,
                                              defaults.HELP_SECTION_INDENT))
            else:
                yield Padding(
                    Columns([self._highlight(item,
                                             console.meta.highlighters.prog)]),
                    (0, 0, 0, defaults.HELP_SECTION_INDENT)
                )

class HelpSectionPlain(HelpSection):
    """Plain text section"""

class HelpSectionUsage(HelpSectionPlain):
    """Usage section in help"""

    def _wrap_usage(self,
                    usage: str,
                    prog: str,
                    *highlighters) -> Union[Text, str]:
        """Wrap usage line"""
        for line in textwrap.wrap(
                usage,
                width=defaults.CONSOLE_WIDTH,
                initial_indent=' ' * defaults.HELP_SECTION_INDENT,
                subsequent_indent=' ' * (defaults.HELP_SECTION_INDENT +
                                         len(prog) + 1),
                break_long_words=False,
                break_on_hyphens=False
        ):
            yield self._highlight(line.replace('*', ' '), highlighters)

    def __rich_console__(self, console: Console, _) -> RenderResult:
        """Implement API from rich to print the help page"""
        for line in self:
            usages = self._wrap_usage(line,
                                      console.meta.prog,
                                      console.meta.highlighters.prog)
            for usage in usages:
                yield Columns([usage])

class HelpSectionOption(HelpSection):
    """Options section in help"""

    def _wrap_opts(self, opts: List[str], *highlighters) -> Union[Text, str]:
        """Wrap the option names and types"""
        for opt in opts:
            for line in textwrap.wrap(
                    opt,
                    width=defaults.HELP_OPTION_WIDTH,
                    initial_indent=' ' * defaults.HELP_SECTION_INDENT,
                    subsequent_indent=' ' * (
                        defaults.HELP_SECTION_INDENT +
                        len(opt.split(",")[0]) + 2
                    ),
                    break_long_words=False,
                    break_on_hyphens=False
            ):
                yield self._highlight(line.replace('*', ' '), highlighters)

    def _wrap_descs(
            self,
            descs: List[str],
            default_highlighter: DefaultHighlighter
    ) -> Union[Text, str]:
        """wrap option descriptions.

        Highlight default value, inline code and code blocks

        Code blocks could be either markdown style:
        ```python
        print('Hello world!')
        ```

        Or a python console style:
        >>> print('Hello world!')
        """
        hillight_inline_code: Callable = (
            lambda text: re.sub(r'(`+)(.+?)\1', r'[code]\2[/code]', text)
        )

        descs = Codeblock.scan_texts(descs, check_default=True)
        def wrap_normal(text):
            for line in textwrap.wrap(
                    text,
                    drop_whitespace=True,
                    width=(defaults.CONSOLE_WIDTH -
                           defaults.HELP_OPTION_WIDTH - 2)
            ):
                yield self._highlight(hillight_inline_code(line))

        for desc in descs: # pylint: disable=too-many-nested-blocks
            if isinstance(desc, Codeblock):
                yield desc.render()

            else:
                sep: Optional[str] = (
                    'Default:' if 'Default:' in desc
                    else 'DEFAULT:' if 'DEFAULT:' in desc
                    else None
                )

                if sep:
                    parts: List[str] = desc.split(sep, 1)
                    # if default is multiline, put it in new line
                    if "\n" in parts[1]:
                        yield from wrap_normal(parts[0])
                        for i, line in enumerate(
                                parts[1].lstrip().splitlines()
                        ):
                            if i == 0:
                                yield Text(sep + ' ' + line, style="default")
                            else:
                                yield Text(" " * (len(sep) + 1) + line,
                                           style="default")
                    else:
                        # use * to connect to avoid default to be wrapped
                        parts[0] += sep + '*' * len(parts[1])

                        # wrap default
                        for line in textwrap.wrap(
                                parts[0],
                                width=(defaults.CONSOLE_WIDTH -
                                       defaults.HELP_OPTION_WIDTH - 2),
                                break_long_words=False,
                                break_on_hyphens=False
                        ):
                            yield self._highlight(
                                Text.from_markup(
                                    hillight_inline_code(line).replace(
                                        sep + '*' * len(parts[1]),
                                        sep + parts[1].replace('[', r'\[')
                                    )
                                ),
                                default_highlighter
                            )
                elif not desc:
                    yield ''
                else:
                    yield from wrap_normal(desc)

    def __rich_console__(self, console: Console, _) -> RenderResult:
        """Implement API from rich to print the help page"""
        table = Table(width=defaults.CONSOLE_WIDTH,
                      show_header=False,
                      show_lines=False,
                      show_edge=False,
                      box=box.SIMPLE,
                      expand=True,
                      pad_edge=False,
                      padding=(0, 0, 0, 0))
        table.add_column(width=defaults.HELP_OPTION_WIDTH)
        table.add_column(width=1)
        table.add_column(width=defaults.CONSOLE_WIDTH -
                         defaults.HELP_OPTION_WIDTH - 1)
        for param_opts, param_descs in self:
            table.add_row(
                Columns(self._wrap_opts(
                    param_opts,
                    console.meta.highlighters.optname,
                    console.meta.highlighters.opttype
                )),
                Text('-', justify='left'),
                Columns(self._wrap_descs(
                    param_descs or [],
                    console.meta.highlighters.default
                ), padding=(0, 0))
            )
        yield table

class HelpAssembler:
    """Assemble a help page

    Attributes:
        console (Console): The console to print the help page
        callback (Callable): The callback to modify the help page
    """

    def __init__(self,
                 prog: str,
                 theme: Union[str, Theme],
                 callback: Optional[Callable]):
        """Constructor

        Args:
            prog (str): The name of the program
            theme (Theme|str): The theme for the help page
        """
        theme = (theme if isinstance(theme, Theme)
                 else THEMES.get(theme, 'default'))

        self.console: Console = Console(
            theme=theme, width=defaults.CONSOLE_WIDTH, tab_size=4
        )
        self.callback: Optional[Callable] = callback
        self._assembled: Optional[List[RenderResult]] = None

        self.console.meta = Diot()
        self.console.meta.prog = prog
        self.console.meta.highlighters = Diot()
        self.console.meta.highlighters.prog = ProgHighlighter(prog)
        self.console.meta.highlighters.optname = OptnameHighlighter()
        self.console.meta.highlighters.opttype = OpttypeHighlighter()
        self.console.meta.highlighters.default = DefaultHighlighter()

    def _assemble_description(self, # pylint: disable=no-self-use
                              params: "Params") -> Optional[HelpSectionPlain]:
        """Assemble the description section"""
        if not params.desc:
            return None

        return HelpSectionPlain(
            desc.format(prog=params.prog) for desc in params.desc
        )

    def _assemble_usage(self, params: "Params") -> HelpSectionUsage:
        """Assemble the usage section"""
        if not params.usage:
            # default usage
            # gather required Arguments
            usage: List[str] = ['{prog}']
            has_optional = False


            for group in params.param_groups.values():
                for param in group:
                    if param.required and param.show:
                        usage.append(param.usagestr())
                    elif param.show:
                        has_optional = True
            if has_optional:
                usage.append('[OPTIONS]')

            if params.commands:
                usage.append('COMMAND [OPTIONS]')

            params.usage = [" ".join(usage)]

        return HelpSectionUsage(
            usage.format(prog=self.console.meta.prog) for usage in params.usage
        )

    def _assemble_param_groups( # pylint: disable=no-self-use
            self,
            params: "Params"
    ) -> Tuple[str, HelpSectionOption]:
        """Assemble the parameter groups"""

        for group, param_list in params.param_groups.items():
            if all(not param.show for param in param_list):
                continue

            yield group, HelpSectionOption(
                ([param.optstr()],
                 param.desc_with_default)
                for param in param_list if param.show
            )

    def _assemble_command_groups( # pylint: disable=no-self-use
            self,
            params: "Params"
    ) -> Tuple[str, HelpSectionOption]:
        """Assemble the command groups"""
        # command groups
        for group, cmd_list in params.command_groups.items():

            yield group, HelpSectionOption(
                ([command.namestr()],
                 command.desc)
                for command in cmd_list
            )

    def assemble(self,
                 params: "Params",
                 printout: bool = False) -> Optional[List[RenderResult]]:
        """Assemble the help page

        Args:
            param (Params): The params object
            printout (bool): Whether to print the help page

        Returns:
            str: The assembled help page
        """
        self._assembled = []

        assembled: OrderedDiot = OrderedDiot()

        assembled_description: Optional[HelpSectionPlain] = (
            self._assemble_description(params)
        )
        if assembled_description:
            assembled.DESCRIPTION = assembled_description

        assembled_usage: HelpSectionPlain = self._assemble_usage(params)
        assembled.USAGE = assembled_usage

        for group, section in self._assemble_param_groups(params):
            assembled[group] = section

        for group, section in self._assemble_command_groups(params):
            assembled[group] = section

        if callable(self.callback):
            self.callback(assembled)

        for title, section in assembled.items():
            self._assembled.append(Text(end="\n"))
            self._assembled.append(Text(title + ':', style="title",
                                        justify="left"))
            self._assembled.append(section)

        if printout:
            self.printout()

        return self._assembled

    def printout(self) -> None:
        """Print the help page"""
        self.console.print(*self._assembled)
