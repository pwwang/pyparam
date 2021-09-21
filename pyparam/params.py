"""Definition of Params"""
import sys
from os import PathLike
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Tuple, Type, Union

import rich
from diot import Diot, OrderedDiot
from simpleconf import LOADERS, Config

from .completer import Completer
from .defaults import PARAM as PARAM_DEFAULT
from .defaults import PARAMS as PARAMS_DEFAULT
from .defaults import POSITIONAL
from .exceptions import PyParamNameError, PyParamTypeError, PyParamValueError
from .help import HelpAssembler, ProgHighlighter
from .param import PARAM_MAPPINGS
from .utils import (
    Namespace,
    always_list,
    logger,
    parse_potential_argument,
    parse_type,
    type_from_value,
)

if TYPE_CHECKING:
    from .help import Theme
    from .param import Param, ParamNamespace, ParamPath


class Params(Completer):
    """Params, served as root params or subcommands

    Args:
        names: The names of this command if served as a command
        desc: The description of the command.
            This will be finally compiled into a list if a string is given.
            The difference is, when displayed on help page, the string will
            be wrapped by textwrap automatically. However, each element in
            a given list will not be wrapped.
        prog: The program name
        help_keys: The names to bring up the help information
        help_cmds: The help command names to show help of other
            subcommands
        help_on_void: Whether to show help when no arguments provided
        help_callback: A function to modify the help page
        help_modifier: A callback function to modify the help param/command
        prefix: The prefix for the arguments
            (see attribute `Params.prefix`)
        arbitrary: Whether to parse the command line arbitrarily
        theme (str|rich.theme.Theme): The theme to render the help page
        usage: Some example usages

    Attributes:
        desc: The description of the command.
        prog: The program name. Default: `sys.argv[0]`
        help_keys: The names to bring up the help information.
        help_cmds: The names of help subcommands to bring up
            help information of subcommands
        help_on_void: Whether show help when there is not arguments
            provided
        usage: The usages of this program
        prefix: The prefix for the arguments on command line
            - `auto`: Automatically determine the prefix for each argument.
                Basically, `-` for short options, and `--` for long.
                Note that `-` for `-vvv` if `v` is a count option
        arbitrary: Whether parsing the command line arbitrarily
        theme (rich.theme.Theme|str): The theme for the help page
        names: The names of the commands if this serves as sub-command
        params: The ordered dict of registered parameters
        commands: The ordered dict of registered commands
        param_groups: The ordered dict of parameter groups
        command_groups: The ordered dict of command groups
        asssembler: The asssembler to assemble the help page
    """

    def __init__(
        self,
        names: Union[str, List[str]] = None,
        desc: Union[List[str], str] = None,
        prog: str = None,
        help_keys: Union[str, List[str]] = None,
        help_cmds: Union[str, List[str]] = None,
        help_on_void: Union[str, bool] = None,
        help_callback: Callable = None,
        help_modifier: Callable = None,
        prefix: str = "auto",
        arbitrary: Union[str, bool] = False,
        theme: Union[str, "Theme"] = "default",
        usage: Union[str, List[str]] = None,
    ) -> None:
        self.names: List[str] = always_list(names) if names else []
        self.desc: List[str] = (
            PARAMS_DEFAULT.desc
            if desc is None
            else always_list(desc, strip=False, split=False)
        )
        self._prog: str = Path(sys.argv[0]).name if prog is None else prog
        self.help_keys: List[str] = (
            PARAMS_DEFAULT.help_keys
            if help_keys is None
            else always_list(help_keys)
        )
        self.help_cmds: List[str] = (
            PARAMS_DEFAULT.help_cmds
            if help_cmds is None
            else always_list(help_cmds)
        )
        self.help_on_void: bool = (
            PARAMS_DEFAULT.help_on_void
            if help_on_void is None
            else help_on_void
        )
        self.usage = (
            None
            if usage is None
            else always_list(usage, strip=True, split="\n")
        )
        self.prefix = prefix
        self.arbitrary = arbitrary
        self.theme = theme

        self.params = OrderedDiot()
        self.commands = OrderedDiot()

        self.param_groups = OrderedDiot()
        self.command_groups = OrderedDiot()

        self.help_modifier = help_modifier

        self.assembler = HelpAssembler(self.prog, theme, help_callback)
        super().__init__()

    @property
    def prog(self) -> str:
        """Get the program name"""
        return self._prog

    @prog.setter
    def prog(self, value: str):
        """Set the program name and update the help assembler

        Args:
            value: The new program name
        """
        self._prog = value
        self.assembler.console.meta.prog = value
        self.assembler.console.meta.highlighters.prog = ProgHighlighter(value)

    def name(self, which: str = "short") -> str:
        """Get the shortest/longest name of the parameter

        A name is ensured to be returned. It does not mean it is the real
        short/long name, but just the shortest/longest name among all the names

        Args:
            which: Whether get the shortest or longest name
                Could use `short` or `long` for short.

        Returns:
            The shortest/longest name of the parameter
        """
        return list(sorted(self.names, key=len))[0 if "short" in which else -1]

    def namestr(self, sep: str = ", ") -> str:
        """Get all names connected with a separator.

        Args:
            sep: The separator to connect the names

        Returns:
            the connected names
        """
        return sep.join(sorted(self.names, key=len))

    def get_param(self, name: str) -> "Param":
        """Get the parameter by name

        If the parameter is under a namespace, try to get it via the namespace

        Args:
            name: The name of the parameter to get (without prefix)

        Returns:
            The parameter, None if failed
        """
        if name is None:
            return None
        if "." not in name:
            return self.params.get(name)

        ns_param: "ParamNamespace" = self.params.get(name.split(".", 1)[0])
        if not ns_param:
            return None
        ret = ns_param.get_param(name)
        return None if name not in ret.names else ret

    def get_command(self, name: str) -> "Params":
        """Get the command object

        Args:
            name: The name of the command to get

        Returns:
            The command object, None if failed.
        """
        return self.commands.get(name)

    def _set_param(self, param: "Param") -> None:
        """Set the parameter

        When a paraemeter's type is overwritten, we need to replace it with
        the new one in the pool (either self.params or the namespace parameter
        that holds it).
        """
        if param.namespaces(0):
            param.ns_param.push(param, -1)
        else:
            for name in param.names:
                self.params[name] = param

    def add_param(
        self,
        names: Union[str, List[str], "Param"],
        default: Any = None,
        type: Union[str, Type] = None,
        desc: Union[str, List[str]] = None,
        show: bool = None,
        required: bool = None,
        callback: Callable = None,
        group: str = None,
        force: bool = False,
        type_frozen: bool = None,
        argname_shorten: bool = None,
        complete_callback: Callable = None,
        **kwargs,
    ) -> "Param":
        """Add an argument

        Args:
            names: names of the argument or a parameter defined somewhere else
                For example, in case we want to reuse a parameter
                ```python
                param = cmd1.add_param('n,name')
                # reuse it:
                cmd2.add_param(param)
                # other arguments will be ignored, except force
                ```

            default: The default value for the argument
            type: The type of the argument
                Including single value type and complex one
                - Single value types:
                    auto, int, str, float, bool, count, py, json, reset
                - Complex value types:
                    list[<single value type>], ns
            desc: The description of the argument
                This will be finally compiled into a list if a string is given.
                The difference is, when displayed on help page, the string will
                be wrapped by textwrap automatically. However, each element in
                a given list will not be wrapped.
            show: Whether this should be shown on help page.
            required: Whether this argument is required from
                the command line
            callback: Callback to convert parsed values
            group: The group this parameter belongs to.
                Arguments will be grouped by this on the help page.
            force: Whether to force adding parameter if it exists
            type_frozen: Whether allow type overwritting from
                the commone line
            argname_shorten: Whether show shortened name for parameter
                under namespace parameter
            complete_callback: The callback for complete the values of the
                parameter
            **kwargs: Additional keyword arguments

        Raises:
            PyParamNameError: When parameter exists and force is false

        Return:
            Param: The added parameter
        """
        if isinstance(names, (str, list)):
            names: List[str] = always_list(names)
            if type is None:
                if POSITIONAL in names and default is None:
                    type = "list"
                else:
                    type = type_from_value(default)

            maintype, subtype = parse_type(
                type.__name__
                if callable(type)
                else PARAM_DEFAULT.type
                if type is None
                else type
            )

            param = PARAM_MAPPINGS[maintype](  # type: ignore
                names=names,
                default=PARAM_DEFAULT.default if default is None else default,
                desc=PARAM_DEFAULT.desc
                if desc is None
                else always_list(desc, strip=False, split=False),
                prefix=self.prefix,
                show=PARAM_DEFAULT.show if show is None else show,
                required=(
                    PARAM_DEFAULT.required if required is None else required
                ),
                subtype=subtype,
                type_frozen=(
                    PARAM_DEFAULT.type_frozen
                    if type_frozen is None
                    else type_frozen
                ),
                callback=callback,
                argname_shorten=(
                    PARAM_DEFAULT.argname_shorten
                    if argname_shorten is None
                    else argname_shorten
                ),
                complete_callback=complete_callback,
                **kwargs,
            )
        else:
            param = names.copy()

        if any(name in self.help_keys for name in param.names):
            param.is_help = True

        if param.namespaces(0):
            # add namespace parameter automatically
            if param.namespaces(0)[0] not in self.params:  # type: ignore
                self.add_param(param.namespaces(0), type="ns")  # type: ignore

            ns_param: "ParamNamespace" = self.params[
                param.namespaces(0)[0]
            ]  # type: ignore
            ns_param.push(param)

        else:
            for name in param.names:
                # check if parameter has been added
                if not force and (
                    (name in self.params and self.params[name] is not param)
                    or name in self.commands
                ):
                    raise PyParamNameError(
                        f"Argument {name!r} has already been added."
                    )
                self.params[name] = param

        group = group or param.default_group
        # leave the parameters here under namespace to have flexibility
        # assigning different groups
        groups: List["Param"] = self.param_groups.setdefault(group, [])

        # any parameter with param.names hasn't been added
        if not any(set(param.names) & set(prm.names) for prm in groups):
            groups.append(param)
        return param

    def add_command(
        self,
        names: Union["Params", str, List[str]],
        desc: Union[str, List[str]] = "No description",
        help_keys: Union[str, List[str]] = "__inherit__",
        help_cmds: Union[str, List[str]] = "__inherit__",
        help_on_void: Union[str, bool] = "__inherit__",
        help_callback: Callable = None,
        help_modifier: Callable = None,
        prefix: str = "__inherit__",
        arbitrary: Union[str, bool] = "__inherit__",
        theme: Union[str, rich.theme.Theme] = "__inherit__",
        usage: Union[str, List[str]] = None,
        group: str = None,
        force: bool = False,
    ) -> "Params":
        """Add a sub-command

        Args:
            names: list of names of this command
                It can also be a Params object that served as a subcommand
            desc: description of this command
            help_keys: help key for bring up help for this command
            help_cmds: help command for printing help for other
                sub-commands of this command
            help_on_void: whether printing help when no arguments passed
            help_callback: callback to manipulate help page
            prefix: prefix for arguments for this command
            arbitray: whether do arbitray Parsing
            theme: The theme of help page for this command
            usage: Usage for this command
            group: Group of this command
            force: Force adding when command exists already.

        Returns:
            The added command
        """
        command: "Params" = None
        if isinstance(names, Params):
            command = names
            command.prog = (
                f"{self.prog}{' [OPTIONS]' if self.params else ''} "
                f"{command.name('long')}"
            )
        else:
            names: List[str] = always_list(names)
            command: "Params" = Params(
                desc=desc,
                prog=(
                    f"{self.prog}{' [OPTIONS]' if self.params else ''} "
                    f"{sorted(names, key=len)[-1]}"
                ),
                help_keys=(
                    self.help_keys if help_keys == "__inherit__" else help_keys
                ),
                help_cmds=(
                    self.help_cmds if help_cmds == "__inherit__" else help_cmds
                ),
                help_on_void=(
                    self.help_on_void
                    if help_on_void == "__inherit__"
                    else help_on_void
                ),
                help_callback=help_callback,
                help_modifier=help_modifier,
                prefix=(self.prefix if prefix == "__inherit__" else prefix),
                arbitrary=(
                    self.arbitrary if arbitrary == "__inherit__" else arbitrary
                ),
                theme=(self.theme if theme == "__inherit__" else theme),
                usage=usage,
                names=names,
            )
        for cmd in command.names:
            # check if command has been added
            if not force and (cmd in self.params or cmd in self.commands):
                raise PyParamNameError(
                    f"Command {cmd!r} has already been added."
                )
            self.commands[cmd] = command

        group = group or "COMMANDS"
        groups: List["Params"] = self.command_groups.setdefault(group, [])

        if not any(set(command.names) & set(cmd.names) for cmd in groups):
            groups.append(command)
        return command

    def print_help(self, exit_code: int = 1) -> None:
        """Print the help information and exit

        Args:
            exit_code: The exit code or False to not exit
        """
        self.assembler.assemble(self)
        self.assembler.printout()
        if exit_code is not False:
            sys.exit(exit_code)

    def values(
        self, namespace: Namespace = None, ignore_errors: bool = False
    ) -> Namespace:
        """Get a namespace of all parameter name => value pairs or attach them
        to the given namespace

        Args:
            namespace: The namespace for the values to attach to.

        Returns:
            the namespace with values of all parameter
                name-value pairs
        """
        ns_no_callback: Namespace = Namespace()
        for param_name, param in self.params.items():
            if param.is_help or param_name in ns_no_callback:
                continue
            try:
                value: Any = param.value
            except (PyParamTypeError, PyParamValueError) as pve:
                if not ignore_errors:
                    logger.error("%r: %s", param.namestr(), pve)
                    self.print_help()
            except Exception:
                if not ignore_errors:
                    raise
            else:
                for name in param.names:
                    ns_no_callback[name] = value

        if namespace is None:
            namespace = Namespace()

        for param_name, param in self.params.items():
            if param.is_help or param_name in namespace:
                continue
            try:
                value: Any = param.apply_callback(ns_no_callback)
            except (PyParamTypeError, PyParamValueError) as pte:
                if not ignore_errors:
                    logger.error("%r: %s", param.namestr(), pte)
                    self.print_help()
            except Exception:
                if not ignore_errors:
                    raise
            else:
                for name in param.names:
                    setattr(namespace, name, value)
        return namespace

    def parse(
        self, args: List[str] = None, ignore_errors: bool = False
    ) -> Namespace:
        """Parse the arguments from the command line

        Args:
            args: The arguments to parse
            ignore_errors: Whether to ignore errors.
                This is helpful to check a specific option or command,
                but ignore errors, such as required options not provided.

        Return:
            Namespace: The namespace of parsed arguments
        """
        # add help options here so that user can disable or
        # change it before parsing
        self.add_param(
            self.help_keys,
            type="bool",
            desc="Print help information for this command",
            force=True,
        )

        help_cmd: "Params" = None
        if self.commands:
            help_cmd = self.add_command(
                self.help_cmds, desc="Print help of sub-commands", force=True
            )
            help_cmd.add_param(
                POSITIONAL,
                type="choice",
                default="",
                desc=(
                    "Command name to print help for. "
                    "Available commands are: {}".format(
                        ", ".join(
                            cmd
                            for cmd in self.commands
                            if cmd not in self.help_cmds
                        )
                    )
                ),
                choices=list(self.commands),
            )

        if callable(self.help_modifier):
            self.help_modifier(self.get_param(self.help_keys[0]), help_cmd)

        if args is None:
            # enable completion only when we are trying to parse sys.argv
            if self.comp_shell:
                print("\n".join(self.complete()))
                sys.exit(0)
            args = sys.argv[1:]

        if not args and self.help_on_void:
            self.print_help()

        namespace: Namespace = Namespace()
        self._parse(args, namespace, ignore_errors)

        # # Allow command to be not provided.
        # if self.commands and not namespace.__command__:
        #     logger.error('No command given.')
        #     self.print_help()
        # run help subcommand
        if (
            namespace.__command__ in self.help_cmds
            and len(self.commands) > 1  # together with help command
        ):
            command_passed = namespace[namespace.__command__][POSITIONAL]
            if not command_passed:
                self.print_help()
            elif command_passed not in self.commands:
                logger.error("Unknown command: %r", command_passed)
                self.print_help()
            else:
                self.commands[command_passed].print_help()
        return namespace

    def _parse(
        self,
        args: List[str],
        namespace: Namespace,
        ignore_errors: bool,
    ) -> None:
        """Parse the arguments from the command line

        Args:
            args: The arguments to parse
            namespace: The namespace for parsed arguments to
                attach to.
        """
        logger.debug("Parsing %r", args)

        if not args:  # help_on_void = False
            self.values(namespace, ignore_errors)
            return

        prev_param: "Param" = None
        for i, arg in enumerate(args):
            logger.debug("- Parsing item %r", arg)
            # Match the arg with defined parameters
            # If arbitrary, non-existing parameters will be created on the fly
            # This means
            # 1. if param_name is None
            #    arg is not a parameter-like format (ie. -a, --arg)
            #    then param_value == arg
            # 2. if param_name is not None, arg is parameter-like
            #    With arbitrary = True, parameter will be created on the fly
            # 3. if arg is like --arg=1, then param_value 1 is pushed to param.
            param, param_name, param_type, param_value = self._match_param(arg)
            logger.debug("  Previous: %r", prev_param)
            logger.debug(
                "  Matched: %r, name=%s, type=%s, value=%r",
                param,
                param_name,
                param_type,
                param_value,
            )
            # as long as the help argument hit
            if param_name in self.help_keys or (param and param.is_help):
                self.print_help()

            if param:
                if prev_param:
                    logger.debug("  Closing previous argument")
                    prev_param.close()
                prev_param = param

            elif prev_param:  # No param
                if param_name is not None:
                    if not ignore_errors:
                        logger.warning("Unknown argument: %r, skipped", arg)
                elif not prev_param.consume(param_value):
                    # If value cannot be consumed, let's see if it
                    # 1. hits a command
                    # 2. hits the start of positional arguments
                    prev_param.close()
                    prev_param, matched = self._match_command_or_positional(
                        prev_param,
                        param_value,
                        args[(i + 1) :],
                        namespace,
                        ignore_errors,
                    )
                    if matched == "command":
                        break
                    if matched == "positional":
                        continue
                    if param_value is not None and not ignore_errors:
                        logger.warning(
                            "Unknown value: %r, skipped", param_value
                        )
                else:
                    logger.debug(
                        "  Param %r consumes %r",
                        prev_param.namestr(),
                        param_value,
                    )
            else:  # neither
                prev_param, matched = self._match_command_or_positional(
                    prev_param,
                    param_value,
                    args[(i + 1) :],
                    namespace,
                    ignore_errors,
                )
                if matched == "command":
                    break
                if matched == "positional":
                    continue
                if param_value is not None and not ignore_errors:
                    logger.warning("Unknown value: %r, skipped", param_value)

        if prev_param:
            logger.debug("  Closing final argument: %r", prev_param.namestr())
            prev_param.close()

        self.values(namespace, ignore_errors)

    def _match_command_or_positional(
        self,
        prev_param: "Param",
        arg: str,
        rest_args: List[str],
        namespace: Namespace,
        ignore_errors: bool = False,
    ) -> Tuple["Param", str]:
        """Check if arg hits a command or a positional argument start

        Args:
            prev_param: The previous parameter
            arg: The current argument item
            rest_args: The remaining argument items

        Returns:
            tuple (Param, str):
                - A parameter if we create a new one here
                    (ie, a positional parameter)
                - 'command' when arg hits a command or 'positional' when it
                    hits the start of a positional argument. Otherwise, None.
        """
        if prev_param and prev_param.is_positional:
            logger.debug("  Hit positional argument")
            prev_param.push(arg)
            return prev_param, "positional"

        if arg not in self.commands:
            # any of the rest args matches is argument-like then
            # this should not hit the start of positional argument
            for rest_arg in rest_args:
                if self.prefix != "auto" and rest_arg.startswith(self.prefix):
                    break

                if self.prefix == "auto" and rest_arg[:1] == "-":
                    if len(rest_arg) <= 2 or (
                        rest_arg[:2] == "--" and len(rest_arg) > 3
                    ):
                        break
            else:
                logger.debug("  Hit start of positional argument")
                if self.arbitrary and POSITIONAL not in self.params:
                    self.add_param(POSITIONAL)
                if POSITIONAL in self.params:
                    self.params[POSITIONAL].hit = True
                    self.params[POSITIONAL].push(arg)
                    return self.params[POSITIONAL], "positional"

        if prev_param:
            prev_param.close()

        if self.arbitrary and arg not in self.commands:
            self.add_command(arg)

        if arg not in self.commands:
            return None, None

        logger.debug("* Hit command: %r", arg)
        command: "Params" = self.commands[arg]
        namespace.__command__ = arg
        parsed: Namespace = command.parse(rest_args, ignore_errors)
        for name in command.names:
            namespace[name] = parsed

        return None, "command"

    def _match_param(self, arg: str) -> Tuple["Param", str, str, str]:
        """Check if arg matches any predefined parameters. With
        arbitrary = True, parameters will be defined on the fly.

        And then do all the preparation for the matched parameter, including
        overwrite the type and push the attached value, such as '--arg=1'

        Args:
            arg: arg to check

        Returns:
            The matched parameter, parameter name,
                type and unpushed value if matched.
                Otherwise, None, param_name, param_type and arg itself.
        """
        param_name, param_type, param_value = parse_potential_argument(
            arg, self.prefix
        )
        # parse -arg as -a rg only applicable with prefix auto and -
        # When we didn't match any argument-like
        # with allow_attached=False
        # Or we matched but it is not defined
        name_with_attached: str = None
        if not param_type and self.prefix == "auto":
            # then -a1 will be put in param_value, as if `a1` is a name,
            # it should be --a1
            name_with_attached = (
                param_value
                if (
                    param_name is None
                    and param_value
                    and param_value[:1] == "-"
                    and param_value[1:2] != "-"
                )
                else None
            )

        elif not param_type and len(self.prefix) <= 1:
            # say prefix = '+'
            # then `a1` for `+a1` will be put as param_name, since
            # there is no restriction on name length
            name_with_attached = (
                self.prefix + param_name
                if param_name and param_name[:1] != self.prefix
                else None
            )

        # we cannot find a parameter with param_name
        # check if there is any value attached
        if name_with_attached and not self.get_param(param_name):
            param_name2, param_type2, param_value2 = parse_potential_argument(
                name_with_attached, self.prefix, allow_attached=True
            )
            # Use them only if we found a param_name2 and
            # arbitrary: not previous param_name found
            # otherwise: parameter with param_name2 exists
            if param_name2 is not None and (
                (self.arbitrary and param_name is None)
                or self.get_param(param_name2)
            ):
                param_name, param_type, param_value = (
                    param_name2,
                    param_type2,
                    param_value2,
                )

        # create the parameter for arbitrary
        if (
            self.arbitrary
            and param_name is not None
            and not self.get_param(param_name)
        ):
            self.add_param(param_name, type=param_type)

        param: "Param" = self.get_param(param_name)
        if not param:
            return None, param_name, param_type, param_value

        param_maybe_overwritten: "Param" = param.overwrite_type(param_type)
        if param_maybe_overwritten is not param:
            self._set_param(param_maybe_overwritten)
            param = param_maybe_overwritten

        param.hit = True
        if param_value is not None:
            param.push(param_value)
        return param, param_name, param_type, param_value

    def _all_params(self, show_only=False) -> List["Param"]:
        """All parameters under this command

        self.params don't have all of them, since namespaced ones are under
        namespace paramters
        """
        ret: List["Param"] = []
        ret_append: Callable = ret.append
        for param in self.params.values():
            if param.type == "ns":
                if (not show_only or param.show) and param not in ret:
                    ret.append(param)
                ret.extend(param.decendents(show_only))

            elif show_only and not param.show:
                continue
            elif param not in ret:
                ret_append(param)
        return ret

    def _to_dict_params(self) -> Diot:
        """Load all parameters into a dictionary"""
        ret = Diot()
        param_groups = {}
        for group, param_list in self.param_groups.items():
            for param in param_list:
                param_groups[param.names[0]] = group

        for param in self._all_params():
            param_name: str = (
                "POSITIONAL"
                if param.names[0] == POSITIONAL
                else param.names[0]
            )
            ret[param_name] = Diot()
            param_dict: Diot = ret[param_name]
            if len(param.names) > 1:
                param_dict.aliases = [
                    "POSITIONAL" if name == POSITIONAL else name
                    for name in param.names[1:]
                ]
            if param.default != PARAM_DEFAULT.default:
                param_dict.default = param.default
            if param.typestr() != PARAM_DEFAULT.type:
                param_dict.type = param.typestr()
            if param.desc != PARAM_DEFAULT.desc:
                param_dict.desc = param.desc
            if param.show != PARAM_DEFAULT.show:
                param_dict.show = param.show
            if param.required != PARAM_DEFAULT.required:
                param_dict.required = param.required
            if param.type_frozen != PARAM_DEFAULT.type_frozen:
                param_dict.type_frozen = param.type_frozen
            if param.argname_shorten != PARAM_DEFAULT.argname_shorten:
                param_dict.argname_shorten = param.argname_shorten
            param_dict.group = group = param_groups[param.names[0]]
            param_dict |= param._kwargs

        return ret

    def _to_dict_commands(self) -> Diot:
        """Load all commands into a dictionary"""
        ret = Diot()
        command_groups = {}
        for group, command_list in self.command_groups.items():
            for command in command_list:
                for name in command.names:
                    command_groups[name] = group

        for command_name, command in self.commands.items():
            if any(name in ret for name in command.names):
                continue
            ret[command_name] = Diot()
            cmd_dict: Diot = ret[command_name]
            if len(command.names) > 1:
                cmd_dict.aliases = [
                    name for name in command.names if name != command_name
                ]
            if command.desc != PARAMS_DEFAULT.desc:
                cmd_dict.desc = command.desc
            if command.help_keys != PARAMS_DEFAULT.help_keys:
                cmd_dict.help_keys = command.help_keys
            if command.help_cmds != PARAMS_DEFAULT.help_cmds:
                cmd_dict.help_cmds = command.help_cmds
            if command.help_on_void != PARAMS_DEFAULT.help_on_void:
                cmd_dict.help_on_void = command.help_on_void
            if command.prefix != PARAMS_DEFAULT.prefix:
                cmd_dict.prefix = command.prefix
            if command.arbitrary != PARAMS_DEFAULT.arbitrary:
                cmd_dict.arbitrary = command.arbitrary
            if command.theme != PARAMS_DEFAULT.theme:
                cmd_dict.theme = command.theme
            if command.usage != PARAMS_DEFAULT.usage:
                cmd_dict.usage = command.usage
            cmd_dict.group = command_groups[command_name]
            cmd_dict |= command.to_dict()

        return ret

    def to_dict(self) -> Diot:
        """Save the parameters/commands to file.

        This is helpful if the parameters/commands take time to load. Once can
        cache this to a file, and load it from it using `from_file`.

        Returns:
            The complied Diot of parameters and commands
        """
        # load all parameters and commands
        return Diot(
            params=self._to_dict_params(), commands=self._to_dict_commands()
        )

    def to_file(self, path: Union[str, Path], cfgtype: str = None) -> None:
        """Save the parameters/commands to file.

        This is helpful if the parameters/commands take time to load. Once can
        cache this to a file, and load it from it using `from_file`.

        Args:
            path: The path to the file
            cfgtype: The type of the file
                If not given, will inferred from the suffix of the path
                Supports one of yaml, toml and json
        """
        loaded: Diot = self.to_dict()
        if not isinstance(path, Path):
            path = Path(path)
        if not cfgtype:
            if path.suffix in (".yml", ".yaml"):
                cfgtype = "yaml"
            elif path.suffix == ".toml":
                cfgtype = "toml"
            elif path.suffix == ".json":
                cfgtype = "json"
            else:
                cfgtype = path.suffix
        if cfgtype not in ("yaml", "json", "toml"):
            raise ValueError("File type not supported: %s" % cfgtype)

        if cfgtype == "yaml":
            loaded.to_yaml(path)
        elif cfgtype == "json":
            loaded.to_json(path)
        else:
            loaded.to_toml(path)

    def from_file(
        self,
        filename: Union[str, PathLike, dict],
        filetype: str = None,
        show: bool = True,
        force: bool = False,
    ) -> None:
        """Load parameters from file

        We support 2 types for format to load the parameters.

        - express way, which has some limitations:
            1. no command definition;
            2. no namespace parameters;
        ```toml
        arg = 1 # default value
        "arg.desc" = "An argument" # description
        # other attributes
        ```
        or
        ```toml
        [arg]
        default = 1
        desc = "An argument"
        ```

        - full specification
        ```toml
        [params.arg]
        default = 1
        desc = "An argument"
        [commands.command]
        desc = "A subcommand"

          [commands.command.params.arg]
          default = 2
          desc = "An argument for command"
        ```

        Args:
            filename: path to the file
            filetype: The type of the file. If None, will infer from the
                filename. Supported types: ini, cfg, conf, config, yml, yaml,
                json, env, osenv, toml
            show: The default show value for parameters in the file
            force: Whether to force adding params/commands
        """
        config: Config = Config(with_profile=False)
        config._load(filename, factory=LOADERS.get(filetype))
        self.from_dict(config, show=show, force=force)

    def _from_dict_with_sections(
        self,
        dict_obj: Dict[str, Dict[str, dict]],
        show: bool = True,
        force: bool = False,
    ) -> None:
        """Load from the dict with 'params' and/or 'commands' sections"""

        param_section: Dict[str, dict] = dict_obj.get("params", {})
        # Type: str, dict
        for param_name, param_attrs in param_section.items():
            param_attrs.setdefault("show", show)
            names: List[str] = always_list(param_attrs.pop("aliases", []))
            names.insert(0, param_name)
            self.add_param(
                [
                    POSITIONAL if name == "POSITIONAL" else name
                    for name in names
                ],
                **param_attrs,
                force=force,
            )

        command_section: Dict[str, dict] = dict_obj.get("commands", {})
        for command_name, command_attrs in command_section.items():
            names: List[str] = always_list(command_attrs.pop("aliases", []))
            names.insert(0, command_name)
            param_section: Dict[str, dict] = command_attrs.pop("params", {})
            subcmd_section: Dict[str, dict] = command_attrs.pop("commands", {})
            command: "Params" = self.add_command(
                names, **command_attrs, force=force
            )
            command.from_dict(
                {"params": param_section, "commands": subcmd_section}, show
            )

    def from_dict(
        self,
        dict_obj: dict,
        show: bool = True,
        force: bool = False,
    ):
        """Load parameters from python dict

        Args:
            dict_obj: A python dictionary to load parameters from
            show: The default show value for the parameters in the
                dictionary
            force: Whether to force adding params/commands
        """
        if "params" not in dict_obj and "commands" not in dict_obj:
            # express way
            # scan and create dict for all params
            all_params: Dict[str, dict] = {}
            for key, val in dict_obj.items():
                param_name: str = key
                if "." in key:
                    param_name = key.split(".", 1)[0]
                all_params.setdefault(param_name, {})

            # scan for the attributes
            for key, val in dict_obj.items():
                if key in all_params:
                    # if it is a dict, and there is not other attributes
                    # assigned like "arg.desc", that means this dictionary
                    # contains all attributes
                    if isinstance(val, dict) and not any(
                        ap_key.startswith(f"{key}.") for ap_key in dict_obj
                    ):
                        all_params[key] = val
                    else:
                        all_params[key]["default"] = val
                elif "." in key:
                    # Type: str, str
                    param_name, param_attr = key.split(".", 1)
                    all_params[param_name][param_attr] = val

            dict_obj = {"params": all_params}

        self._from_dict_with_sections(dict_obj, show, force)

    def from_arg(
        self,
        names: Union[str, List[str], "ParamPath"],
        desc: Union[str, List[str]] = "The configuration file.",
        group: str = None,
        default: Union[str, Path] = None,
        show: bool = True,
        force: bool = False,
        args: List[str] = None,
    ):
        """Load parameters from the file specified by naargument
        from command line

        This will load the parameters from the file given by the argument,
        ignoring other arguments from the command line. One can overwrite
        some of them afterwards, and do the parsing finally.

        Args:
            names: The names of the parameter or
                the parameter itself. If it is the parameter, other
                arguments are ignored
            desc: The description of the parameter
            group: The group of the parameter
            default: The default value of the file path
            show: Whether those parameters should show up in the help page
            force: Whether to force adding the parameters/commands
            args: The list of items to parse, otherwise
                parse sys.argv[1:]
        """
        if isinstance(names, (str, list)):
            param: "Param" = self.add_param(
                names, desc=desc, group=group, type="path", default=default
            )
        else:
            param: "Param" = names
            self._set_param(names)

        prefixed_names: List[str] = [
            param._prefix_name(name) for name in param.names
        ]
        args: List[str] = sys.argv[1:] if args is None else args
        args_with_the_arg: List[str] = []
        for i, arg in enumerate(args):
            if arg in prefixed_names:
                args_with_the_arg.append(arg)
                if i < len(args) - 1:
                    args_with_the_arg.append(args[i + 1])
                break
        filepath: Union[str, Path] = (
            args_with_the_arg[1] if len(args_with_the_arg) > 1 else param.value
        )
        if filepath:
            self.from_file(filepath, show=show, force=force)

    def __repr__(self):
        return "<Params(%s) @ %s>" % (",".join(self.names), id(self))

    def copy(self, deep=False) -> "Params":
        """Copy a Params object

        Args:
            deep: Whether to copy the parameters and commands deeply

        Returns:
            The copied params object
        """
        copied: "Params" = Params(
            names=self.names[:],
            desc=self.desc[:],
            prog=self.prog,
            help_keys=self.help_keys[:],
            help_cmds=self.help_cmds[:],
            help_on_void=self.help_on_void,
            help_callback=None,
            help_modifier=self.help_modifier,
            prefix=self.prefix,
            arbitrary=self.arbitrary,
            theme=self.theme,
            usage=self.usage and self.usage[:],
        )
        copied.assembler = self.assembler

        if not deep:
            copied.params = self.params.copy()
            copied.commands = self.commands.copy()

            copied.param_groups = self.param_groups.copy()
            copied.command_groups = self.command_groups.copy()
        else:
            copied.params = OrderedDiot()
            copied.commands = OrderedDiot()

            copied.param_groups = OrderedDiot()
            copied.command_groups = OrderedDiot()

            for param in self.params.values():
                if any(name in copied.params for name in param.names):
                    continue
                param_copy = param.copy()
                for name in param.names:
                    copied.params[name] = param_copy

            for command in self.commands.values():
                if any(name in copied.commands for name in command.names):
                    continue
                command_copy = command.copy(deep=deep)
                for name in command.names:
                    copied.commands[name] = command_copy

            for group, param_list in self.param_groups.items():
                self.param_groups[group] = [
                    copied.get_param(param.names[0]) for param in param_list
                ]
            for group, cmd_list in self.command_groups.items():
                self.command_groups[group] = [
                    copied.commands[cmd.names[0]] for cmd in cmd_list
                ]

        return copied
