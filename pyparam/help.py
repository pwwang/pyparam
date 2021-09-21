"""Help assembler for pyparam

Attributes:
    THEMES: The theme for the help page.
"""
import re
import textwrap
from typing import TYPE_CHECKING, Callable, Dict, List, Tuple, Type, Union

from diot import Diot, OrderedDiot
from rich import box  # , print
from rich.console import Console, RenderGroup, RenderResult
from rich.highlighter import RegexHighlighter
from rich.padding import Padding
from rich.table import Table
from rich.text import Text
from rich.theme import Theme

from . import defaults
from .utils import Codeblock

if TYPE_CHECKING:
    from .params import Params

THEMES: Dict[str, Theme] = dict(
    default=Theme(
        dict(
            title="bold cyan",
            prog="bold green",
            default="magenta",
            optname="bright_green",
            opttype="blue italic",
            opttype_frozen="blue",
        )
    ),
    synthware=Theme(
        dict(
            title="bold magenta",
            prog="bold yellow",
            default="cyan",
            optname="bright_yellow",
            opttype="bright_red italic",
            opttype_frozen="bright_red",
        )
    ),
)


class ProgHighlighter(RegexHighlighter):
    """Apply style to anything that looks like a program name.

    Args:
        prog: The program name
    """

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

    def _highlight(
        self,
        string: str,
        highlighters: List[Type[RegexHighlighter]] = None,
    ) -> Union[Text, str]:
        """Highlight the string using given highlighters"""
        if not highlighters:
            return string
        if not isinstance(highlighters, (tuple, list)):
            highlighters = [highlighters]  # type: ignore
        for highlighter in highlighters:
            string = highlighter(string)  # type: ignore

        return string

    def __rich_console__(self, console: Console, _) -> RenderResult:
        """Implement API from rich to print the help page"""
        scanned = Codeblock.scan_texts(self)
        for item in scanned:
            if isinstance(item, Codeblock):
                yield Padding(
                    item.render(), (0, 0, 0, defaults.HELP_SECTION_INDENT)
                )
            else:
                yield Padding(
                    self._highlight(item, console.meta.highlighters.prog),
                    (0, 0, 0, defaults.HELP_SECTION_INDENT),
                )


class HelpSectionPlain(HelpSection):
    """Plain text section"""


class HelpSectionUsage(HelpSectionPlain):
    """Usage section in help"""

    def _wrap_usage(  # type: ignore
        self, usage: str, prog: str, *highlighters
    ) -> Union[Text, str]:
        """Wrap usage line"""
        for line in textwrap.wrap(
            usage,
            width=defaults.CONSOLE_WIDTH,
            initial_indent=" " * defaults.HELP_SECTION_INDENT,
            subsequent_indent=" "
            * (defaults.HELP_SECTION_INDENT + len(prog) + 1),
            break_long_words=False,
            break_on_hyphens=False,
        ):
            yield self._highlight(
                line.replace("*", " "),
                highlighters,  # type: ignore
            )

    def __rich_console__(self, console: Console, _) -> RenderResult:
        """Implement API from rich to print the help page"""
        for line in self:
            usages = self._wrap_usage(
                line, console.meta.prog, console.meta.highlighters.prog
            )

            yield RenderGroup(*usages)  # type: ignore


class HelpSectionOption(HelpSection):
    """Options section in help"""

    def _wrap_opts(  # type: ignore
        self,
        opts: List[str],
        *highlighters,
    ) -> Union[Text, str]:
        """Wrap the option names and types"""
        for opt in opts:
            for line in textwrap.wrap(
                opt,
                width=defaults.HELP_OPTION_WIDTH,
                initial_indent=" " * defaults.HELP_SECTION_INDENT,
                subsequent_indent=" "
                * (defaults.HELP_SECTION_INDENT + 4),
                break_long_words=False,
                break_on_hyphens=False,
            ):
                yield self._highlight(
                    line.replace("*", " "),
                    highlighters,  # type: ignore
                )

    def _wrap_descs(  # type: ignore
        self, descs: List[str], default_highlighter: DefaultHighlighter
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
        hillight_inline_code: Callable = lambda text: re.sub(
            r"(`+)(.+?)\1", r"[code]\2[/code]", text
        )

        descs = Codeblock.scan_texts(descs, check_default=True)

        def wrap_normal(text):
            for line in textwrap.wrap(
                text,
                drop_whitespace=True,
                width=(
                    defaults.CONSOLE_WIDTH - defaults.HELP_OPTION_WIDTH - 2
                ),
            ):
                yield self._highlight(hillight_inline_code(line))

        for desc in descs:
            if isinstance(desc, Codeblock):
                yield desc.render()

            else:
                sep: str = (
                    "Default:"
                    if "Default:" in desc
                    else "DEFAULT:"
                    if "DEFAULT:" in desc
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
                                yield Text(sep + " " + line, style="default")
                            else:
                                yield Text(
                                    " " * (len(sep) + 1) + line,
                                    style="default",
                                )
                    else:
                        # use * to connect to avoid default to be wrapped
                        parts[0] += sep + "*" * len(parts[1])

                        # wrap default
                        for line in textwrap.wrap(
                            parts[0],
                            width=(
                                defaults.CONSOLE_WIDTH
                                - defaults.HELP_OPTION_WIDTH
                                - 2
                            ),
                            break_long_words=False,
                            break_on_hyphens=False,
                        ):
                            yield self._highlight(
                                Text.from_markup(  # type: ignore
                                    hillight_inline_code(line).replace(
                                        sep + "*" * len(parts[1]),
                                        sep + parts[1].replace("[", r"\["),
                                    )
                                ),
                                default_highlighter,  # type: ignore
                            )
                elif not desc:
                    yield ""
                else:
                    yield from wrap_normal(desc)

    def __rich_console__(self, console: Console, _) -> RenderResult:
        """Implement API from rich to print the help page"""
        table = Table(
            width=defaults.CONSOLE_WIDTH,
            show_header=False,
            show_lines=False,
            show_edge=False,
            box=box.SIMPLE,
            expand=True,
            pad_edge=False,
            padding=(0, 0, 0, 0),
        )
        table.add_column(width=defaults.HELP_OPTION_WIDTH)
        table.add_column(width=1)
        table.add_column(
            width=defaults.CONSOLE_WIDTH - defaults.HELP_OPTION_WIDTH - 1
        )
        for param_opts, param_descs in self:
            table.add_row(
                RenderGroup(  # type: ignore
                    *self._wrap_opts(
                        param_opts,
                        console.meta.highlighters.optname,
                        console.meta.highlighters.opttype,
                    )
                ),
                Text("-", justify="left"),
                RenderGroup(  # type: ignore
                    *self._wrap_descs(
                        param_descs or [], console.meta.highlighters.default
                    )
                ),
            )
        yield table


class HelpAssembler:
    """Assemble a help page

    Args:
        prog: The name of the program
        theme: The theme for the help page

    Attributes:
        console: The console to print the help page
        callback: The callback to modify the help page
    """

    def __init__(
        self, prog: str, theme: Union[str, Theme], callback: Callable
    ):
        """Constructor"""
        theme = (
            theme
            if isinstance(theme, Theme)
            else THEMES.get(theme, "default")  # type: ignore
        )

        self.console: Console = Console(
            theme=theme, width=defaults.CONSOLE_WIDTH, tab_size=4
        )
        self.callback: Callable = callback
        self._assembled: List[RenderResult] = None

        self.console.meta = Diot()
        self.console.meta.prog = prog
        self.console.meta.highlighters = Diot()
        self.console.meta.highlighters.prog = ProgHighlighter(prog)
        self.console.meta.highlighters.optname = OptnameHighlighter()
        self.console.meta.highlighters.opttype = OpttypeHighlighter()
        self.console.meta.highlighters.default = DefaultHighlighter()

    def _assemble_description(
        self, params: "Params"
    ) -> HelpSectionPlain:
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
            usage: List[str] = ["{prog}"]
            has_optional = False

            for group in params.param_groups.values():
                for param in group:
                    if param.required and param.show:
                        usage.append(param.usagestr())
                    elif param.show:
                        has_optional = True
            if has_optional:
                usage.append("[OPTIONS]")

            if params.commands:
                usage.append("COMMAND [OPTIONS]")

            params.usage = [" ".join(usage)]

        return HelpSectionUsage(
            usage.format(prog=params.prog) for usage in params.usage
        )

    def _assemble_param_groups(  # type: ignore
        self, params: "Params"
    ) -> Tuple[str, HelpSectionOption]:
        """Assemble the parameter groups"""

        for group, param_list in params.param_groups.items():
            if all(not param.show for param in param_list):
                continue

            yield group, HelpSectionOption(
                ([param.optstr()], param.desc_with_default)
                for param in param_list
                if param.show
            )

    def _assemble_command_groups(  # type: ignore
        self, params: "Params"
    ) -> Tuple[str, HelpSectionOption]:
        """Assemble the command groups"""
        # command groups
        for group, cmd_list in params.command_groups.items():

            yield group, HelpSectionOption(
                ([command.namestr()], command.desc) for command in cmd_list
            )

    def assemble(self, params: "Params") -> None:
        """Assemble the help page

        Args:
            params: The params object
        """
        self._assembled = []

        assembled: OrderedDiot = OrderedDiot()

        assembled_description: HelpSectionPlain = self._assemble_description(
            params
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
            self._assembled.append(Text(end="\n"))  # type: ignore
            self._assembled.append(
                Text(  # type: ignore
                    title + ":",
                    style="title",
                    justify="left",
                )
            )
            self._assembled.append(section)

    def printout(self) -> None:
        """Print the help page"""
        self.console.print(*self._assembled)
