"""Sub-command support for pyparam"""
import sys
from diot import OrderedDiot
from .defaults import (CMD_GLOBAL_OPTPROXY,
                       OPT_POSITIONAL_NAME,
                       OPTIONAL_OPT_TITLE,
                       REQUIRED_OPT_TITLE)
from .params import Params, ParamsParseError, ParamNameError
from .help import HelpAssembler, Helps, HelpOptions

class CommandsParseError(Exception):
    """Exception to raise while failed to parse
    command arguments from command line"""

class Commands:
    """
    Support sub-command for command line argument parse.
    """

    def __init__(self, theme='default', prefix='auto'):
        """
        Constructor
        @params:
            `theme`: The theme
        """
        self.__dict__['_props'] = dict(
            _desc=[],
            _hcmd=['help'],
            cmds=OrderedDiot(),
            inherit=True,
            assembler=HelpAssembler(None, theme),
            helpx=None,
            prefix=prefix
        )
        self._cmds[CMD_GLOBAL_OPTPROXY] = Params(None, theme)
        self._cmds[CMD_GLOBAL_OPTPROXY]._prefix = prefix
        self._cmds[CMD_GLOBAL_OPTPROXY]._hbald = False

        self._installHelpCommand()

    def _installHelpCommand(self):
        helpcmd = Params(None, self._assembler.theme)
        helpcmd._desc = 'Print help message for the command and exit.'
        helpcmd._hbald = False
        helpcmd[OPT_POSITIONAL_NAME] = ''
        helpcmd[OPT_POSITIONAL_NAME].desc = 'The command.'

        def helpPositionalCommandCallback(param):
            if not param.value or param.value in self._hcmd:
                raise CommandsParseError('__help__')
            if param.value not in self._cmds:
                raise CommandsParseError('No such command: %s' % param.value)
            self._cmds[param.value]._help(print_and_exit=True)
        helpcmd[OPT_POSITIONAL_NAME].callback = helpPositionalCommandCallback
        for hcmd in self._hcmd:
            self._cmds[hcmd] = helpcmd

    def _setInherit(self, inherit):
        self._inherit = inherit

    def _setDesc(self, desc):
        """
        Set the description
        @params:
            `desc`: The description
        """
        self._desc = desc
        return self

    def _setHcmd(self, hcmd):
        """
        Set the help command
        @params:
            `hcmd`: The help command
        """
        for cmd in self._hcmd:
            if cmd in self._cmds:
                del self._cmds[cmd]

        self._props['_hcmd'] = [cmd.strip()
                                for cmd in hcmd.split(',')] \
                               if isinstance(hcmd, str) \
                               else hcmd

        self._installHelpCommand()
        return self

    def _setTheme(self, theme):
        """
        Set the theme
        @params:
            `theme`: The theme
        """
        self._theme = theme
        return self

    def _setPrefix(self, prefix):
        self._prefix = prefix
        return self

    def __getattr__(self, name):
        """
        Get the value of the attribute
        @params:
            `name` : The name of the attribute
        @returns:
            The value of the attribute
        """
        if (name.startswith('__') or
                name.startswith('_%s' % self.__class__.__name__)):
            return getattr(super(Commands, self), name)
        if name in ('_desc', '_hcmd'):
            return self._props[name]
        if name in ('_cmds', '_assembler', '_helpx', '_prefix', '_inherit'):
            return self._props[name[1:]]
        if name not in self._cmds:
            self._cmds[name] = Params(name, self._assembler.theme)
            self._cmds[name]._prefix = self._prefix
        return self._cmds[name]

    def __setattr__(self, name, value):
        """
        Set the value of the attribute
        @params:
            `name` : The name of the attribute
            `value`: The value of the attribute
        """
        if (name.startswith('__') or
                name.startswith('_%s' % self.__class__.__name__)):
            super(Commands, self).__setattr__(name, value)
        elif name == '_theme':
            self._assembler = HelpAssembler(None, value)
        elif name == '_hcmd':
            self._setHcmd(value)
        elif name == '_desc':
            self._props['_desc'] = value.splitlines() \
                                   if isinstance(value, str) \
                                   else value
        elif name == '_prefix':
            self._props['prefix'] = value
            for cmd in self._cmds.values():
                cmd._prefix = value
        elif name in ('_cmds', '_assembler', '_helpx', '_inherit'):
            self._props[name[1:]] = value
        elif isinstance(value, Params): # alias
            self._cmds[name] = value
            if name != value._prog.split()[-1]:
                value._prog += '|' + name
                value._assembler = HelpAssembler(value._prog,
                                                 value._assembler.theme)
        else:
            if name not in self._cmds:
                self._cmds[name] = Params(name, self._assembler.theme)
                self._cmds[name]._prefix = self._prefix
            self._cmds[name]._desc = value

    __getitem__ = __getattr__
    __setitem__ = __setattr__

    def _inheritGlobalOptions(self):
        if not self._inherit:
            return

        globalopts = self._cmds[CMD_GLOBAL_OPTPROXY]
        for name, param in globalopts._params.items():
            if name in globalopts._hopts:
                continue
            for cmd, cmdparams in self._cmds.items():
                if cmd == CMD_GLOBAL_OPTPROXY or cmd in self._hcmd:
                    continue
                if self._cmds[CMD_GLOBAL_OPTPROXY]._prefix != cmdparams._prefix:
                    raise ValueError(
                        'Cannot inheirt global options (%s) with '
                        'inconsistent prefix (%s).' % (
                            self._cmds[CMD_GLOBAL_OPTPROXY]._prefix,
                            cmdparams._prefix)
                    )

                if name in cmdparams._params and cmdparams[name] is not param:
                    raise ParamNameError(
                        ('Cannot have option %r defined for both global and '
                         'command %r\nif you let command inherit global '
                         'options (_inherit = True).') % (name, cmd)
                    )
                cmdparams[name] = param

    def _parse(self, args=None, arbi=False, dict_wrapper=dict):
        """
        Parse the arguments.
        @params:
            `args`: The arguments (list). `sys.argv[1:]`
                will be used if it is `None`.
            `arbi`: Whether do an arbitrary parse.
                If True, options do not need to be defined.
                Default: `False`
        @returns:
            A `tuple` with first element the subcommand and
                second the parameters being parsed.
        """
        # check if inherit is True, then we should also
        # attach global options to commands
        self._inheritGlobalOptions()
        if arbi:
            for hcmd in self._hcmd:
                self._cmds[hcmd][OPT_POSITIONAL_NAME].callback = None

        args = sys.argv[1:] if args is None else args
        # the commands have to be defined even for arbitrary mode
        try:
            if not args:
                raise CommandsParseError('__help__')
            # get which command is hit
            cmdidx = None
            if arbi:
                # arbitrary mode does not have global options
                cmdidx = 0
                if args[cmdidx] not in self._cmds:
                    self._cmds[args[cmdidx]] = Params(args[cmdidx],
                                                      self._assembler.theme)
                    self._cmds[args[cmdidx]]._prefix = self._prefix
            else:
                for i, arg in enumerate(args):
                    if arg != CMD_GLOBAL_OPTPROXY and arg in self._cmds:
                        cmdidx = i
                        break
                else:
                    raise CommandsParseError('No command given.')

            command = args[cmdidx]
            global_args = args[:cmdidx]
            command_args = args[(cmdidx+1):]
            if (self._inherit and command not in self._hcmd):
                command_opts = self._cmds[command]._parse(
                    global_args + command_args, arbi, dict_wrapper)
                global_opts = self._cmds[CMD_GLOBAL_OPTPROXY]._dict(
                    wrapper=dict_wrapper
                )
            else:
                try:
                    global_opts = self._cmds[CMD_GLOBAL_OPTPROXY]._parse(
                        global_args, arbi, dict_wrapper, raise_exc=True)
                except ParamsParseError as exc:
                    raise CommandsParseError(str(exc))
                command_opts = self._cmds[command]._parse(
                    command_args,
                    arbi,
                    dict_wrapper
                )

            return command, command_opts, global_opts

        except CommandsParseError as exc:
            exc = str(exc)
            if exc == '__help__':
                exc = ''
            self._help(error=exc, print_and_exit=True)

    def _help(self, error='', print_and_exit=False):
        """
        Construct the help page
        @params:
            `error`: the error message
            `print_and_exit`: print the help page and exit
                instead of return the help information
        @returns:
            The help information if `print_and_exit` is `False`
        """
        helps = Helps()

        if self._desc:
            helps.add('DESCRIPTION', self._desc)

        helps.add(
            'USAGE',
            '{prog} <command> [OPTIONS]' \
                if self._inherit \
                else '{prog} [GLOBAL OPTIONS] <command> [COMMAND OPTIONS]'
        )

        global_opt_items = self._cmds[CMD_GLOBAL_OPTPROXY]._helpitems
        helps.add('GLOBAL %s' % REQUIRED_OPT_TITLE,
                  global_opt_items[REQUIRED_OPT_TITLE])
        helps.add('GLOBAL %s' % OPTIONAL_OPT_TITLE,
                  global_opt_items[OPTIONAL_OPT_TITLE])

        helps.add('AVAILABLE COMMANDS', HelpOptions(prefix=''))

        revcmds = OrderedDiot()
        for name, command in self._cmds.items():
            if name == CMD_GLOBAL_OPTPROXY:
                continue
            revcmds.setdefault(command, []).append(name)

        for command, names in revcmds.items():
            if self._hcmd[0] in names:
                continue
            helps['AVAILABLE COMMANDS'].add(command, names)

        command_section = helps['AVAILABLE COMMANDS']
        command_section.addCommand(self._cmds[self._hcmd[0]], self._hcmd)
        command_help_index = command_section.query(self._hcmd[0])
        command_help = command_section[command_help_index]
        command_section[command_help_index] = (
            command_help[0],
            '[COMMAND]',
            command_help[2])

        if callable(self._helpx):
            self._helpx(helps)

        ret = []
        if error:
            error = error.splitlines() if isinstance(error, str) else error
            ret = [self._assembler.error(err.strip()) for err in error]

        ret.extend(self._assembler.assemble(helps))

        if not print_and_exit:
            return '\n'.join(ret)

        sys.stderr.write('\n'.join(ret))
        sys.exit(1)

    def _complete(self,
                  shell,
                  auto=False,
                  inherit=True,
                  withtype=False,
                  alias=True,
                  showonly=True):
        from completions import Completions
        completions = Completions(inherit=inherit,
                                  desc=self._desc and self._desc[0] or '')
        revcmds = OrderedDiot()
        for key, val in self._cmds.items():
            if key == CMD_GLOBAL_OPTPROXY:
                continue
            revcmds.setdefault(val, []).append(key)

        if CMD_GLOBAL_OPTPROXY in self._cmds:
            self._cmds[CMD_GLOBAL_OPTPROXY]._addToCompletions(
                completions, withtype, alias, showonly)

        helpoptions = {
            cmdname: (command._desc and command._desc[0] or '')
            for cmdname, command in self._cmds.items()
            if cmdname not in self._hcmd and cmdname != CMD_GLOBAL_OPTPROXY
        }
        for command, names in revcmds.items():
            if not alias:
                names = [list(sorted(names, key=len))[-1]]
            compdesc = command._desc[0] if command._desc else ''
            for name in names:
                if name in self._hcmd:
                    completions.addCommand(name, compdesc, helpoptions)
                else:
                    completions.addCommand(name, compdesc)
                    command._addToCompletions(
                        completions.command(name), withtype, alias, showonly)
        return completions.generate(shell, auto)
