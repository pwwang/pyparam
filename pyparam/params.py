"""Definition of Params"""
import sys
from typing import (
    Optional,
    Type,
    Union,
    List,
    Callable,
    Any,
    Tuple,
    Dict
)
from pathlib import Path
from diot import OrderedDiot
import rich
from simpleconf import Config, LOADERS
from .utils import (
    always_list,
    Namespace,
    logger,
    parse_type,
    type_from_value,
    parse_potential_argument
)
from .defaults import POSITIONAL
from .param import PARAM_MAPPINGS
from .help import HelpAssembler
from .exceptions import (
    PyParamNameError,
    PyParamTypeError
)

class Params: # pylint: disable=too-many-instance-attributes
    """Params, served as root params or subcommands

    Attributes:
        desc (list): The description of the command.
        prog (str): The program name. Default: `sys.argv[0]`
        help_keys (list): The names to bring up the help information.
        help_cmds (list): The names of help subcommands to bring up
            help information of subcommands
        help_on_void (bool): Whether show help when there is not arguments
            provided
        usage (list): The usages of this program
        prefix (str): The prefix for the arguments on command line
            - `auto`: Automatically determine the prefix for each argument.
                Basically, `-` for short options, and `--` for long.
                Note that `-` for `-vvv` if `v` is a count option
        arbitrary (bool): Whether parsing the command line arbitrarily
        theme (rich.theme.Theme|str): The theme for the help page
        names (list): The names of the commands if this serves as sub-command
        params (OrderedDiot): The ordered dict of registered parameters
        commands (OrderedDiot): The ordered dict of registered commands
        param_groups (OrderedDiot): The ordered dict of parameter groups
        command_groups (OrderedDiot): The ordered dict of command groups
        asssembler (HelpAssembler): The asssembler to assemble the help page
    """

    def __init__(self, # pylint: disable=too-many-arguments
                 names: Optional[Union[str, List[str]]] = None,
                 desc: Optional[Union[List[str], str]] = 'No description',
                 prog: str = sys.argv[0],
                 help_keys: Union[str, List[str]] = 'h,help,H',
                 help_cmds: Union[str, List[str]] = 'help',
                 help_on_void: bool = True,
                 help_callback: Optional[Callable] = None,
                 prefix: str = 'auto',
                 arbitrary: bool = False,
                 theme: str = 'default',
                 usage: Optional[Union[str, List[str]]] = None) -> None:
        """Constructor

        Args:
            names (str|list): The names of this command if served as a command
            desc (str|list): The description of the command.
                This will be finally compiled into a list if a string is given.
                The difference is, when displayed on help page, the string will
                be wrapped by textwrap automatically. However, each element in
                a given list will not be wrapped.
            prog (str): The program name
            help_keys (str|list): The names to bring up the help information
            help_cmds (str|list): The help command names to show help of other
                subcommands
            help_on_void (bool): Whether to show help when no arguments provided
            help_callback (callable): A function to modify the help page
            prefix (str): The prefix for the arguments
                (see attribute `Params.prefix`)
            arbitrary (bool): Whether to parse the command line arbitrarily
            theme (str|rich.theme.Theme): The theme to render the help page
            usage (str|list): Some example usages,
        """
        self.desc: List[str] = always_list(desc, strip=False, split=False)
        self.prog: str = prog
        self.help_keys: List[str] = always_list(help_keys)
        self.help_cmds: List[str] = always_list(help_cmds)
        self.help_on_void: bool = help_on_void
        self.usage: Optional[List[str]] = (
            None if usage is None
            else always_list(usage, strip=True, split='\n')
        )
        self.prefix: str = prefix
        self.arbitrary: bool = arbitrary
        self.theme: Union[str, rich.theme.Theme] = theme
        self.names: List[str] = always_list(names) if names else []

        self.params: OrderedDiot = OrderedDiot()
        self.commands: OrderedDiot = OrderedDiot()

        self.param_groups: OrderedDiot = OrderedDiot()
        self.command_groups: OrderedDiot = OrderedDiot()

        self.assembler: HelpAssembler = HelpAssembler(
            prog, theme, help_callback
        )

    def name(self, which: str = 'short') -> str:
        """Get the shortest/longest name of the parameter

        A name is ensured to be returned. It does not mean it is the real
        short/long name, but just the shortest/longest name among all the names

        Args:
            which (str): Whether get the shortest or longest name
                Could use `short` or `long` for short.

        Returns:
            str: The shortest/longest name of the parameter
        """
        return list(sorted(self.names, key=len))[0 if 'short' in which else -1]

    def namestr(self, sep: str = ", ") -> str:
        """Get all names connected with a separator.

        Args:
            sep (str): The separator to connect the names

        Returns:
            str: the connected names
        """
        return sep.join(sorted(self.names, key=len))

    def get_param(self, name: Optional[str]) -> Optional[Type["Param"]]:
        """Get the parameter by name

        If the parameter is under a namespace, try to get it via the namespace

        Args:
            name (str): The name of the parameter to get (without prefix)

        Returns:
            Param: The parameter, None if failed
        """
        if name is None:
            return None
        if '.' not in name:
            return self.params.get(name)

        ns_param: Optional["ParamNamespace"] = self.params.get(
            name.split('.', 1)[0]
        )
        if not ns_param:
            return None
        ret = ns_param.get_param(name)
        return None if name not in ret.names else ret

    def get_command(self, name: str) -> Optional["Params"]:
        """Get the command object

        Args:
            name (str): The name of the command to get

        Returns:
            Params: The command object, None if failed.
        """
        return self.commands.get(name)

    def _set_param(self, param: Type["Param"]) -> None:
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

    def add_param(self, # pylint: disable=too-many-arguments
                  names: Union[str, List[str]],
                  default: Any = None,
                  # pylint: disable=redefined-builtin
                  type: Optional[str] = None,
                  desc: Union[str, List[str]] = None,
                  show: bool = True,
                  required: bool = False,
                  callback: Optional[Callable] = None,
                  group: Optional[str] = None,
                  force: bool = False,
                  type_fronzen: bool = True,
                  argname_shorten: bool = True,
                  **kwargs) -> Type["Param"]:
        """Add an argument

        Args:
            names (str|list): names of the argument
            default (any): The default value for the argument
            type (str|callable): The type of the argument
                Including single value type and complex one
                - Single value types:
                    auto, int, str, float, bool, count, py, json, reset
                - Complex value types:
                    list[<single value type>], ns
            desc (str|list): The description of the argument
                This will be finally compiled into a list if a string is given.
                The difference is, when displayed on help page, the string will
                be wrapped by textwrap automatically. However, each element in
                a given list will not be wrapped.
            show (bool): Whether this should be shown on help page.
            required (bool): Whether this argument is required from
                the command line
            callback (callable): Callback to convert parsed values
            group (str): The group this parameter belongs to.
                Arguments will be grouped by this on the help page.
            force (bool): Whether to force adding paramter if it exists
            type_frozen (bool): Whether allow type overwritting from
                the commone line
            argname_shorten (bool): Whether show shortened name for parameter
                under namespace parameter
            **kwargs: Additional keyword arguments

        Raises:
            PyParamNameError: When parameter exists and force is false

        Return:
            Param: The added parameter
        """
        # pylint: disable=too-many-locals
        names: List[str] = always_list(names)
        if type is None:
            if POSITIONAL in names and default is None:
                type = 'list'
            else:
                type = type_from_value(default)

        # Type: Optional[str], Optional[str]
        maintype, subtype = parse_type(type.__name__
                                       if callable(type)
                                       else type)

        param: Type['Param'] = PARAM_MAPPINGS[maintype](
            names=names,
            default=default,
            desc=None if desc is None else always_list(desc, strip=False,
                                                       split=False),
            prefix=self.prefix,
            show=show,
            required=required,
            subtype=subtype,
            type_fronzen=type_fronzen,
            callback=callback,
            argname_shorten=argname_shorten,
            **kwargs
        )
        if any(name in self.help_keys for name in names):
            param.is_help = True

        if param.namespaces(0):
            # add namespace parameter automatically
            if param.namespaces(0)[0] not in self.params:
                self.add_param(param.namespaces(0), type="ns")

            ns_param: "ParamNamespace" = self.params[param.namespaces(0)[0]]
            ns_param.push(param)

        else:
            for name in names:
                # check if parameter has been added
                if not force and (name in self.params or name in self.commands):
                    raise PyParamNameError(
                        f"Argument {name} has already been added."
                    )
                self.params[name] = param

        group = group or param.default_group
        # leave the parameters here under namespace to have flexibility
        # assigning different groups
        groups: List[Type['Param']] = self.param_groups.setdefault(group, [])

        # any parameter with param.names hasn't been added
        if not any(set(param.names) & set(prm.names) for prm in groups):
            groups.append(param)
        return param

    def add_command(self, # pylint: disable=too-many-arguments
                    names: Union[str, List[str]],
                    desc: Optional[Union[str, List[str]]] = 'No description',
                    help_keys: Union[str, List[str]] = '__inherit__',
                    help_cmds: Union[str, List[str]] = '__inherit__',
                    help_on_void: Union[str, bool] = '__inherit__',
                    help_callback: Optional[Callable] = None,
                    prefix: str = '__inherit__',
                    arbitrary: Union[str, bool] = '__inherit__',
                    theme: Union[str, rich.theme.Theme] = '__inherit__',
                    usage: Optional[Union[str, List[str]]] = None,
                    group: Optional[str] = None,
                    force: bool = False) -> "Params":
        """Add a sub-command

        Args:
            names (list): list of names of this command
            desc (str|list): description of this command
            help_keys (str|list): help key for bring up help for this command
            help_cmds (str|list): help command for printing help for other
                sub-commands of this command
            help_on_void (bool): whether printing help when no arguments passed
            help_callback (callable): callback to manipulate help page
            prefix (str): prefix for arguments for this command
            arbitray (bool): whether do arbitray Parsing
            theme (str): The theme of help page for this command
            usage (str|list): Usage for this command
            group (str): Group of this command
            force (bool): Force adding when command exists already.

        Returns:
            Params: The added command
        """
        # pylint: disable=too-many-locals
        commands: List[str] = always_list(names)
        command: "Params" = Params(
            desc=desc,
            prog=(f"{self.prog}{' [OPTIONS]' if self.params else ''} "
                  f"{sorted(commands, key=len)[-1]}"),
            help_keys=(self.help_keys if help_keys == '__inherit__'
                       else help_keys),
            help_cmds=(self.help_cmds if help_cmds == '__inherit__'
                       else help_cmds),
            help_on_void=(self.help_on_void if help_on_void == '__inherit__'
                          else help_on_void),
            help_callback=help_callback,
            prefix=(self.prefix if prefix == '__inherit__'
                    else prefix),
            arbitrary=(self.arbitrary
                       if arbitrary == '__inherit__'
                       else arbitrary),
            theme=(self.theme if theme == '__inherit__'
                   else theme),
            usage=usage,
            names=commands
        )
        for cmd in commands:
            # check if command has been added
            if not force and (cmd in self.params or cmd in self.commands):
                raise PyParamNameError(
                    f"Command {cmd!r} has already been added."
                )
            self.commands[cmd] = command

        group = group or "COMMANDS"
        groups: List['Params'] = self.command_groups.setdefault(group, [])

        if not any(set(command.names) & set(cmd.names) for cmd in groups):
            groups.append(command)
        return command

    def _print_help(self, just_try: bool = False, exit_code: int = 1) -> None:
        """Print the help information and exit

        Args:
            just_try (bool): Whether we are just trying parsing, don't exit
                nor print help.
            exit_code (int|bool): The exit code or False to not exit
        """
        if just_try:
            return

        self.assembler.assemble(self, printout=True)
        if exit_code is not False:
            sys.exit(exit_code)

    def values(self,
               namespace: Optional[Namespace] = None) -> Optional[Namespace]:
        """Get a namespace of all paramter name => value pairs or attach them
        to the given namespace

        Args:
            namespace (Namespace): The namespace for the values to attach to.

        Returns:
            Namespace: the namespace with values of all parameter
                name-value pairs
        """
        ns_no_callback: Namespace = Namespace()
        for param_name, param in self.params.items():
            if param.is_help or param_name in ns_no_callback:
                continue
            try:
                value: Any = param.value
            except (TypeError, ValueError) as pve:
                logger.error("%r: %s", param.namestr(), pve)
                self._print_help()
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
            except PyParamTypeError as pte:
                logger.error("%r: %s", param.namestr(), pte)
                self._print_help()
            else:
                for name in param.names:
                    setattr(namespace, name, value)

        return namespace

    def parse(self,
              args: Optional[List[str]] = None,
              just_try: bool = False) -> Namespace:
        """Parse the arguments from the command line

        Args:
            args (list): The arguments to parse
            just_try (bool): Just try parsing, don't exit nor print the help.
                See what we can get from the command line

        Return:
            Namespace: The namespace of parsed arguments
        """
        # add help options here so that user can disable or
        # change it before parsing
        self.add_param(self.help_keys,
                       type='bool',
                       desc='Print help information for this command',
                       force=True)

        if self.commands:
            help_cmd: "Params" = self.add_command(
                self.help_cmds,
                desc='Print help of sub-commands',
                force=True
            )
            help_cmd.add_param(
                POSITIONAL,
                type='str',
                default="",
                desc="Command name to print help for"
            )

        args = sys.argv[1:] if args is None else args

        if not args and self.help_on_void:
            self._print_help(just_try)

        namespace: Namespace = Namespace()
        self._parse(args, namespace, just_try)

        if self.commands and not namespace.__command__:
            logger.error('No command given.')
            self._print_help(just_try)
        # run help subcommand
        elif (
                namespace.__command__ in self.help_cmds and
                len(self.commands) > 1 # together with help command
        ):
            command_passed = namespace[namespace.__command__][POSITIONAL]
            if not command_passed:
                self._print_help(just_try)
            elif command_passed not in self.commands:
                logger.error('Unknown command: %r', command_passed)
                self._print_help(just_try)
            else:
                self.commands[command_passed]._print_help(just_try)
        return namespace

    def _parse(self, # pylint: disable=too-many-branches
               args: List[str],
               namespace: Namespace,
               just_try: bool = False) -> None:
        """Parse the arguments from the command line

        Args:
            args (list): The arguments to parse
            namespace (Namespace): The namespace for parsed arguments to
                attach to.
            just_try (bool): Just try parsing, don't print help nor exit
        """
        logger.debug("Parsing %r", args)

        if not args: # help_on_void = False
            self.values(namespace)
            return

        prev_param: Optional[Type['Param']] = None
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
            # Type: Optional[Type['Param']], Optional[str], Optional[str], Any
            param, param_name, param_type, param_value = self._match_param(arg)
            logger.debug("  Previous: %r", prev_param)
            logger.debug("  Matched: %r, name=%s, type=%s, value=%r",
                         param, param_name, param_type, param_value)
            # as long as the help argument hit
            if param_name in self.help_keys or (param and param.is_help):
                self._print_help(just_try)

            if param:
                if prev_param:
                    logger.debug("  Closing previous argument")
                    prev_param.close()
                prev_param = param

            elif prev_param: # No param
                if param_name is not None:
                    logger.warning("Unknown argument: %r, skipped", arg)
                elif not prev_param.consume(param_value):
                    # If value cannot be consumed, let's see if it
                    # 1. hits a command
                    # 2. hits the start of positional arguments
                    # Type: Optional[Type['Param']], Optional[str]
                    prev_param, matched = self._match_command_or_positional(
                        prev_param, param_value, args[(i+1):], namespace
                    )
                    if matched == 'command':
                        break
                    if matched == 'positional':
                        continue
                    logger.warning("Unknown value: %r, skipped", param_value)
                else:
                    logger.debug("  Param %r consumes %r",
                                 prev_param.namestr(), param_value)

            else: # neither
                # Type: Optional[Type['Param']], Optional[str]
                prev_param, matched = self._match_command_or_positional(
                    prev_param, param_value, args[(i+1):], namespace
                )
                if matched == 'command':
                    break
                if matched == 'positional':
                    continue
                logger.warning("Unknown value: %r, skipped", param_value)

        if prev_param:
            prev_param.close()

        self.values(namespace)

    def _match_command_or_positional(
            self,
            prev_param: Optional[Type['Param']],
            arg: str,
            rest_args: List[str],
            namespace: Namespace
    ) -> Tuple[Optional[Type['Param']], Optional[str]]:
        """Check if arg hits a command or a positional argument start

        Args:
            prev_param (Param): The previous parameter
            arg (str): The current argument item
            rest_args (list): The remaining argument items

        Returns:
            tuple (Param, str):
                - A parameter if we create a new one here
                    (ie, a positional parameter)
                - 'command' when arg hits a command or 'positional' when it hits
                    the start of a positional argument. Otherwise, None.
        """
        if prev_param and prev_param.is_positional:
            logger.debug("  Hit positional argument")
            prev_param.push(arg)
            return prev_param, 'positional'

        if arg not in self.commands:
            # any of the rest args matches is argument-like then
            # this should not hit the start of positional argument
            for rest_arg in rest_args:
                if self.prefix != 'auto' and rest_arg.startswith(self.prefix):
                    break

                if self.prefix == 'auto' and rest_arg[:1] == '-':
                    if len(rest_arg) <= 2 or (
                            rest_arg[:2] == '--' and len(rest_arg) > 3
                    ):
                        break
            else:
                logger.debug("  Hit start of positional argument")
                if self.arbitrary and POSITIONAL not in self.params:
                    self.add_param(POSITIONAL)
                if POSITIONAL in self.params:
                    self.params[POSITIONAL].hit = True
                    self.params[POSITIONAL].push(arg)
                    return self.params[POSITIONAL], 'positional'

        if prev_param:
            prev_param.close()

        if self.arbitrary and arg not in self.commands:
            self.add_command(arg)

        if arg not in self.commands:
            return None, None

        logger.debug("* Hit command: %r", arg)
        command: "Params" = self.commands[arg]
        namespace.__command__ = arg
        parsed: Namespace = command.parse(rest_args)
        for name in command.names:
            namespace[name] = parsed

        return None, 'command'

    def _match_param(self, arg: str) -> Tuple[
            Optional[Type['Param']],
            Optional[str],
            Optional[str],
            Optional[str]
    ]:
        """Check if arg matches any predefined parameters. With
        arbitrary = True, parameters will be defined on the fly.

        And then do all the preparation for the matched parameter, including
        overwrite the type and push the attached value, such as '--arg=1'

        Args:
            arg (str): arg to check

        Returns:
            tuple (Param, str, str, str): The matched parameter, parameter name,
                type and unpushed value if matched.
                Otherwise, None, param_name, param_type and arg itself.
        """
        # Type: Optional[str], Optional[str], Optional[str]
        param_name, param_type, param_value = parse_potential_argument(
            arg, self.prefix
        )
        # parse -arg as -a rg only applicable with prefix auto and -
        # When we didn't match any argument-like
        # with allow_attached=False
        # Or we matched but it is not defined
        if ( # pylint:disable=too-many-boolean-expressions
                not param_type and param_value and param_value[:1] == (
                    '-' if self.prefix == 'auto' else self.prefix
                ) and (param_name is None or (
                    not self.arbitrary and not self.get_param(param_name)
                ))
        ):
            # parsed '-arg' as '-a rg'
            # Type: Optional[str], Optional[str], Optional[str]
            param_name2, param_type2, param_value2 = (
                parse_potential_argument(
                    arg, self.prefix, allow_attached=True
                )
            )
            if param_name2 is not None and (
                    param_name is None or (
                        not self.arbitrary and
                        not self.get_param(param_name2)
                    )
            ):
                param_name, param_type, param_value = (
                    param_name2, param_type2, param_value2
                )

        if (self.arbitrary and
                param_name is not None and
                not self.get_param(param_name)):
            self.add_param(param_name, type=param_type)

        param: Optional[Type['Param']] = self.get_param(param_name)
        if not param:
            return None, param_name, param_type, param_value

        param_maybe_overwritten: Type['Param'] = param.overwrite_type(
            param_type
        )
        if param_maybe_overwritten is not param:
            self._set_param(param_maybe_overwritten)
            param = param_maybe_overwritten

        param.hit = True
        if param_value is not None:
            param.push(param_value)

        return param, param_name, param_type, param_value

    def from_file(self,
                  filename: Union[str, dict],
                  filetype: Optional[str] = None,
                  show: bool = True) -> None:
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
            filename (str): path to the file
            filetype (str): The type of the file. If None, will infer from the
                filename.
                Supported types: ini, cfg, conf, config, yml, yaml, json
                env, osenv, toml
            show (bool): The default show value for parameters in the file
        """
        config: Config = Config(with_profile=False)
        config._load(filename, factory=LOADERS.get(filetype))

        self.from_dict(config, show=show)

    def _from_dict_with_sections(self,
                                 dict_obj: Dict[str, Dict[str, dict]],
                                 show: bool = True) -> None:
        """Load from the dict with 'params' and/or 'commands' sections"""

        param_section: Dict[str, dict] = dict_obj.get('params', {})
        # Type: str, dict
        for param_name, param_attrs in param_section.items():
            param_attrs.setdefault('show', show)
            names: List[str] = always_list(param_attrs.pop('aliases', []))
            names.insert(0, param_name)
            self.add_param(names, **param_attrs)

        command_section: Dict[str, dict] = dict_obj.get('commands', {})
        for command_name, command_attrs in command_section.items():
            names: List[str] = always_list(command_attrs.pop('aliases', []))
            names.insert(0, command_name)
            param_section: Dict[str, dict] = command_attrs.pop('params', {})
            command: "Params" = self.add_command(names, **command_attrs)
            command.from_dict({"params": param_section}, show)

    def from_dict(self, dict_obj: dict, show: bool = True):
        """Load parameters from python dict

        Args:
            dict_obj (dict): A python dictionary to load parameters from
            show (bool): The default show value for the parameters in the
                dictionary
        """
        if 'params' not in dict_obj and 'commands' not in dict_obj:
            # express way
            # scan and create dict for all params
            all_params: Dict[str, dict] = {}
            for key, val in dict_obj.items():
                param_name: str = key
                if '.' in key:
                    param_name = key.split('.', 1)[0]
                all_params.setdefault(param_name, {})

            # scan for the attributes
            for key, val in dict_obj.items():
                if key in all_params:
                    # if it is a dict, and there is not other attributes
                    # assigned like "arg.desc", that means this dictionary
                    # contains all attributes
                    if (isinstance(val, dict) and
                            not any(ap_key.startswith(f"{key}.")
                                    for ap_key in dict_obj)):
                        all_params[key] = val
                    else:
                        all_params[key]['default'] = val
                elif '.' in key:
                    # Type: str, str
                    param_name, param_attr = key.split('.', 1)
                    all_params[param_name][param_attr] = val

            dict_obj = {"params": all_params}

        self._from_dict_with_sections(dict_obj, show)

    def from_arg(self, # pylint: disable=too-many-arguments
                 names: Union[str, List[str], 'ParamPath'],
                 desc: Union[str, List[str]] = "The configuration file.",
                 group: Optional[str] = None,
                 args: Optional[List[str]] = None,
                 required: bool = True):
        """Load parameters from the file specified by naargument
        from command line

        This will load the paramters from the file given by the argument,
        ignoring other arguments from the command line. One can overwrite
        some of them afterwards, and do the parsing finally.

        Args:
            names (str|list|ParamPath): The names of the parameter or
                the parameter itself. If it is the parameter, other
                arguments are ignored
            desc (str|list): The description of the parameter
            group (str): The group of the parameter
            required (bool): Whether this argument is required
            args (list): The list of items to parse, otherwise
                parse sys.argv[1:]
        """
        if isinstance(names, (str, list)):
            param: "ParamPath" = self.add_param(
                names, desc=desc, required=required, group=group, type='path'
            )
        else:
            param: "ParamPath" = names
            self._set_param(names)

        prefixed_names: List[str] = [param._prefix_name(name)
                                     for name in param.names]

        args: List[str] = sys.argv[1:] if args is None else args
        args_with_the_arg: List[str] = []
        for i, arg in enumerate(args):
            if arg in prefixed_names:
                args_with_the_arg.append(arg)
                if i < len(args) - 1:
                    args_with_the_arg.append(args[i+1])
                break

        parsed: Namespace = self.parse(args, just_try=True)
        path: Path = parsed[param.name('short', False)]
        if path:
            self.from_file(path)

# pylint: disable=invalid-name
params: Params = Params()
