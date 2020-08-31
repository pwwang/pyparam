"""Definition of Params"""
import sys
from diot import OrderedDiot
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
    PyParamUnsupportedParamType,
    PyParamAlreadyExists,
    PyParamValueError
)

class Params:
    """Params, served as root params or subcommands

    Attributes:
        desc (list): The description of the command.
        prog (str): The program name. Default: `sys.argv[0]`
        help_keys (list): The names to bring up the help information.
        prefix (str): The prefix for the arguments on command line
            - `auto`: Automatically determine the prefix for each argument.
                Basically, `-` for short options, and `--` for long.
                Note that `-` for `-vvv` if `v` is a count option
        usage (list): Some example usages of the command
    """

    def __init__(self,
                 desc='No description',
                 prog=sys.argv[0],
                 help_keys='h,help,H',
                 help_cmds='help',
                 help_on_void=True,
                 help_callback=None,
                 prefix='auto',
                 arbitrary=False,
                 theme='default',
                 usage=None,
                 names=None):
        """Constructor

        Args:
            desc (str|list): The description of the command.
                This will be finally compiled into a list if a string is given.
                The difference is, when displayed on help page, the string will
                be wrapped by textwrap automatically. However, each element in
                a given list will not be wrapped.
            prog (str): The program name
            help_keys (str|list): The names to bring up the help information
            prefix (str): The prefix for the arguments
                (see attribute `Params.prefix`)
            usage (str|list): Some example usages
        """
        self.desc = always_list(desc, strip=False, split=False)
        self.prog = prog
        self.help_keys = always_list(help_keys)
        self.help_cmds = always_list(help_cmds)
        self.help_on_void = help_on_void
        self.usage = (None if usage is None
                      else always_list(usage, strip=False, split=False))
        self.prefix = prefix
        self.arbitrary = arbitrary
        self.theme = theme
        self.names = names or []

        self.params = OrderedDiot()
        self.commands = OrderedDiot()

        self.param_groups = OrderedDiot()
        self.command_groups = OrderedDiot()

        self.assembler = HelpAssembler(prog, theme, prefix, help_callback)

    def name(self, which='short'):
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

    def namestr(self, sep=", ", sort='asc'):
        """Get all names connected with a separator.

        Args:
            sep (str): The separator to connect the names
            sort (str|bool): Whether to sort the names by length,
                or False to not sort
        Returns:
            str: the connected names
        """
        names = [name
                 for name in (
                     self.names
                     if not sort
                     else sorted(self.names, key=len)
                     if sort == 'asc'
                     else sorted(self.names, key=lambda x: -len(x))
                 )]
        return sep.join(names)

    def add_param(self,
                  names,
                  default=None,
                  type=None, # pylint: disable=redefined-builtin
                  desc='No description',
                  show=True,
                  required=False,
                  callback=None,
                  group=None,
                  force=False):
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
            callback (callable): Callback to convert parsed values
            force (bool): Whether to force adding paramter if it exists

        Raises:
            PyParamAlreadyExists: When parameter exists and force is false

        Return:
            Param: The added parameter
        """
        if type is None:
            type = type_from_value(default)

        maintype, subtype = parse_type(type.__name__
                                       if callable(type)
                                       else type)

        if maintype not in PARAM_MAPPINGS:
            raise PyParamUnsupportedParamType(
                f"Param type {type} is not supported."
            )

        names = always_list(names)
        param = PARAM_MAPPINGS[maintype](
            names=names,
            default=default,
            desc=None if desc is None else always_list(desc, strip=False,
                                                       split=False),
            prefix=self.prefix,
            show=show,
            required=required,
            subtype=subtype,
            callback=callback
        )

        for name in names:
            # check if parameter has been added
            if not force and (name in self.params or name in self.commands):
                raise PyParamAlreadyExists(
                    f"Argument {name} has already been added."
                )
            self.params[name] = param

        group = group or (f"{'REQUIRED' if required else 'OPTIONAL'} OPTIONS:")
        self.param_groups.setdefault(group, []).append(param)

        return param

    def add_command(self,
                    commands,
                    desc='No description',
                    help_keys='__inherit__',
                    help_cmds='__inherit__',
                    help_on_void='__inherit__',
                    help_callback=None,
                    prefix='__inherit__',
                    arbitrary='__inherit__',
                    theme='__inherit__',
                    usage=None,
                    group=None,
                    force=False):
        """Add a sub-command

        Args:
            commands (list): list of names of this command
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
        commands = always_list(commands)
        command = Params(
            desc=desc,
            prog=f"{self.prog} {commands[0]}",
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
                raise PyParamAlreadyExists(
                    f"Command {cmd!r} has already been added."
                )
            self.commands[cmd] = command

        group = group or "COMMANDS"
        self.command_groups.setdefault(group, []).append(command)

        return command

    def parse(self, args=None):
        """Parse the arguments from the command line

        Args:
            args (list): The arguments to parse
            arbi (bool): Do an arbitrary parsing?
                Arbitrary parsing does not required parameters to be predefined.
                They are defined on the fly.

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
            help_cmd = self.add_command(
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
            self.print_help()

        namespace = Namespace()
        self._parse(args, namespace)

        if self.commands and not namespace.__command__:
            logger.error('No command given.')
            self.print_help()
        # run help subcommand
        elif (
                namespace.__command__ in self.help_cmds and
                len(self.commands) > 1 # together with help command
        ):
            command_passed = namespace[namespace.__command__][POSITIONAL]
            if not command_passed:
                self.print_help()
            elif command_passed not in self.commands:
                logger.error('Unknown command: %r', command_passed)
                self.print_help()
            else:
                self.commands[command_passed].print_help()
        return namespace

    def print_help(self, exit_code=1):
        """Print the help information and exit

        Args:
            exit_code (int|bool): The exit code or False to not exit
        """
        self.assembler.assemble(self, printout=True)
        if exit_code is not False:
            sys.exit(exit_code)

    def values(self, namespace=None):
        """Get a dict of paramter name => value pairs or attach them to the
        given namespace

        Args:
            namespace (Namespace): The namespace for the values to attach to.

        Returns:
            dict|NoneType: None if namespace is specified otherwise dict of
                name-value pairs
        """
        ret = {}
        for param_name, param in self.params.items():
            try:
                value = param.value()
            except PyParamValueError as pve:
                logger.error(str(pve))
                self.print_help()
            else:
                if param_name in self.help_keys:
                    continue
                if namespace is not None:
                    setattr(namespace, param_name, value)
                else:
                    ret[param_name] = value
        return None if namespace else ret

    def _clearup_prev_param(self,
                            prev_param,
                            param_name,
                            param_type,
                            param_value,
                            prev_first_hit):
        """Clear up the previous parameter and try to create a new one
        And do proper stuff with the type and value"""
        if not prev_param and not param_name:
            logger.debug("  No previous argument and not an argument at %r",
                         param_value)
            return None, None

        if prev_param and param_name:
            param = None
            first_hit = True
            logger.debug("  Hit another argument: %r", param_name)
            # previous parameter is bool and can take value, but this value
            # cannot be taken, so give it True
            if prev_param.type == 'bool' and prev_first_hit:
                logger.debug("  * Setting previous parameter to True")
                prev_param.push('true')
            # we hit the same argument
            elif param_name in prev_param.names:
                if param_type == 'reset' and prev_param.type == 'list':
                    logger.debug("  * Resetting previous list parameter: %r",
                                 prev_param.namestr())
                    prev_param._stack = []
                    param = prev_param
                    first_hit = 'reset'
                elif prev_param.type != param_type:
                    logger.warning("Type changed from %r to %r for argument %r",
                                   prev_param.type,
                                   param_type,
                                   prev_param.namestr())
                    param = prev_param.to(param_type)
                    for name in param.names:
                        self.params[name] = param
                else:
                    param = prev_param
            # different argument hit
            if not param:
                if self.arbitrary and param_name not in self.params:
                    self.add_param(param_name, type=param_type)
                param = self.params[param_name]

            if param_value is not None:
                param.push(param_value, first=first_hit)
                first_hit = False

            return param, first_hit

        if prev_param: # didn't hit new argument
            # When should we consume the value?
            # If prev_first_hit is True, we should clear previous stack
            # and warn
            # But we should not do it for list parameter
            if prev_first_hit and prev_param.type != 'list':
                if prev_param._stack:
                    logger.warning("Value of previous argument %r lost",
                                   prev_param.namestr())
                prev_param._stack = []

            if prev_param.should_consume(param_value):
                prev_param.push(param_value, first=prev_first_hit)
                return prev_param, False
            return None, None

        # if param_name:
        if self.arbitrary and param_name not in self.params:
            self.add_param(param_name, type=param_type)
        param = self.params[param_name]

        if param_value is not None:
            param.push(param_value, first=True)
            return param, False

        return param, True

    def _parse(self, args, namespace):
        """Parse the arguments from the command line

        Args:
            args (list): The arguments to parse
            namespace (Namespace): The namespace for parsed arguments to
                attach to.
        """
        logger.debug("Parsing %r", args)

        if not args:
            return

        param = None
        first_hit = False
        for i, arg in enumerate(args):
            logger.debug("- Parsing item %r", arg)
            param_name, param_type, param_value = self._match_param(arg)
            # unmatched argument
            if (not self.arbitrary and param_name is None and
                    param_value is None):
                continue

            # if we hit help keys anyway
            if param_name in self.help_keys:
                self.print_help()

            param, first_hit = self._clearup_prev_param(
                param,
                param_name,
                param_type,
                param_value,
                first_hit
            )

            # we have cleared up this arg
            if param:
                continue

            # we didn't hit any argument for arg

            # this is a pending value
            # let's see if this is the starting of positional arguments
            # otherwise, this should be a subcommand
            if arg in self.commands:
                logger.debug("  Hit command: %r", arg)
                namespace.__command__ = arg
                namespace[arg] = self.commands[arg].parse(args[(i+1):])
                break

            if not self.arbitrary:

                if (POSITIONAL in self.params and
                        self._maybe_positional(args[(i+1):])):
                    logger.debug("  Hit the start %r "
                                 "of the POSITIONAL argument", arg)

                    param = self.params[POSITIONAL]
                    param.push(param_value, first=True)
                    first_hit = False
                else:
                    logger.warning("Unmatched value: %r", arg)
            else:

                if self._maybe_positional(args[(i+1):]):
                    logger.debug("  Hit the start %r "
                                "of the POSITIONAL argument", arg)
                    if POSITIONAL not in self.params:
                        self.add_param(POSITIONAL, type='list')
                    param = self.params[POSITIONAL]
                    param.push(param_value, first=True)
                    first_hit = False
                else:
                    logger.debug("  Hit subcommand %r", arg)
                    if arg not in self.commands:
                        self.commands[arg] = Params(
                            prog=f'{self.prog} {arg}',
                            help_keys=self.help_keys,
                            help_on_void=self.help_on_void,
                            arbitrary=True
                        )
                    namespace.__command__ = arg
                    namespace[arg] = self.commands[arg].parse(args[(i+1):])
                    break


        self.values(namespace)

    def _maybe_positional(self, rest):
        """See if we start to hit positional arguments"""
        for arg in rest:
            if self.prefix != 'auto' and arg.startswith(self.prefix):
                return False

            if self.prefix == 'auto' and arg[:1] == '-':
                if len(arg) <= 2 or (arg[:2] == '--' and len(arg) > 3):
                    return False
        else:
            return True

    def _match_param(self, arg):
        """Check if arg matches any predefined parameters

        Args:
            arg (str): arg to check

        Returns:
            tuple (str, str, str): The matched parameter name,
                type and unpushed value.
                if matched. Otherwise, None, None and arg itself.
        """

        param_name, param_type, param_value = parse_potential_argument(
            arg, self.prefix
        )
        if self.arbitrary:
            return param_name, param_type, param_value

        if param_name is None:
            return None, None, arg

        if param_name not in self.params:
            # try argument with attached value
            param_name2, param_type2, param_value2 = parse_potential_argument(
                arg, self.prefix
            )
            if param_name2 is not None and param_name2 in self.params:
                param_name, param_type, param_value = (
                    param_name2, param_type2, param_value2
                )

        if param_name not in self.params:
            logger.warning("Unknown argument: %s", param_name)
            # skip this item
            return None, None, None

        param = self.params[param_name]
        if param_type and param_type != param.type and param_type != 'reset':
            logger.warning("Type changed of argument %r from %r to %r",
                           param.namestr(), param.type, param_type)
            new_param = param.to(param_type)
            for name in param.names:
                self.params[name] = new_param
        return param_name, param_type, param_value

# pylint: disable=invalid-name
params = Params()
