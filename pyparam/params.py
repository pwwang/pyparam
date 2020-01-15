"""Params for pyparam"""

import sys
import re
import builtins
from os import path
from collections import OrderedDict
from simpleconf import Config
from .help import (HelpItems,
                   HelpOptions,
                   Helps,
                   HelpAssembler)
from .utils import _Hashable, wraptext
from .param import Param, ParamTypeError, ParamNameError
from .defaults import (OPT_UNSET_VALUE,
                       OPT_POSITIONAL_NAME,
                       OPT_BOOL_PATTERN,
                       OPT_PATTERN,
                       REQUIRED_OPT_TITLE,
                       OPTIONAL_OPT_TITLE,
                       MAX_WARNINGS,
                       MAX_PAGE_WIDTH)

class ParamsParseError(Exception):
    """Exception to raise while failed to parse arguments from command line"""

class ParamsLoadError(Exception):
    """Exception to raise while failed to load params from dict/file"""

class Params(_Hashable):
    """
    A set of parameters
    """

    def __init__(self, command=None, theme='default'):
        """
        Constructor
        @params:
            `command`: The sub-command
            `theme`: The theme
        """
        prog = path.basename(sys.argv[0])
        prog = prog + ' ' + command if command else prog
        self.__dict__['_props'] = dict(
            prog=prog,
            usage=[],
            desc=[],
            hopts=['h', 'help', 'H'],
            prefix='auto',
            hbald=True,
            assembler=HelpAssembler(prog, theme),
            helpx=None,
            locked=False,
            lockedkeys=[]
        )
        self.__dict__['_params'] = OrderedDict()
        self._set_hopts(self._hopts)

    def __setattr__(self, name, value):
        """
        Change the value of an existing `Param` or create a `Param`
        using the `name` and `value`. If `name` is an attribute,
        return its value.
        @params:
            `name` : The name of the Param
            `value`: The value of the Param
        """
        if (name.startswith('__') or
                name.startswith('_%s' % self.__class__.__name__)):
            super(Params, self).__setattr__(name, value)
        elif isinstance(value, Param): # set alias
            if value.type == 'verbose:' and len(name) == 1:
                raise ParamNameError(
                    'Cannot alias verbose option to a short option'
                )
            self._params[name] = value
        elif name == '_locked':
            if not self._locked and value:
                self._lockedkeys = list(self._params.keys())
            elif not value:
                self._lockedkeys = []
            self._props['locked'] = bool(value)
        elif name in self._lockedkeys and self._locked:
            raise ParamNameError(
                'Parameters are locked and parameter {0!r} exists. '
                'To change the value of an existing parameter, '
                'use \'params.{0}.value = xxx\''.format(name)
            )
        elif name in self._params:
            self._params[name].value = value
        elif name in ('_assembler', '_helpx', '_prog', '_lockedkeys'):
            self._props[name[1:]] = value
        elif name in ['_' + key for key in self._props.keys()] + ['_theme']:
            getattr(self, '_set_%s' % name[1:])(value)
        else:
            self._params[name] = Param(name, value)

    def __getattr__(self, name):
        """
        Get a `Param` instance if possible, otherwise return an attribute value
        @params:
            `name`: The name of the `Param` or the attribute
        @returns:
            A `Param` instance if `name` exists in `self._params`, otherwise,
            the value of the attribute `name`
        """
        if (name.startswith('__') or
                name.startswith('_%s' % self.__class__.__name__)):
            return getattr(super(Params, self), name)
        if name in ('_' + key for key in self._props.keys()):
            return self._props[name[1:]]
        if name not in self._params:
            self._params[name] = Param(name)
        elif (self._locked and
              name in self._lockedkeys and
              not self._params[name].show):
            self._params[name]._should_raise = True
        return self._params[name]

    __getitem__ = __getattr__
    __setitem__ = __setattr__

    def _set_theme(self, theme):
        """
        Set the theme
        @params:
            `theme`: The theme
        """
        self._props['assembler'] = HelpAssembler(self._prog, theme)
        return self

    def _set_usage(self, usage):
        """
        Set the usage
        @params:
            `usage`: The usage
        """
        assert isinstance(usage, (list, str))
        self._props['usage'] = usage if isinstance(usage, list) \
                                     else usage.splitlines()
        return self

    def _set_desc(self, desc):
        """
        Set the description
        @params:
            `desc`: The description
        """
        assert isinstance(desc, (list, str))
        self._props['desc'] = desc if isinstance(desc, list) \
                                   else desc.splitlines()
        return self

    def _set_hopts(self, hopts):
        """
        Set the help options
        @params:
            `hopts`: The help options
        """
        if hopts is None:
            raise ValueError('No option specified for help.')
        assert isinstance(hopts, (list, str))
        # remove all previous help options
        for hopt in self._hopts:
            if hopt in self._params:
                del self._params[hopt]

        self._props['hopts'] = hopts if isinstance(hopts, list) \
                                     else [ho.strip()
                                           for ho in hopts.split(',')]
        if any('.' in hopt for hopt in self._hopts):
            raise ValueError('No dot allowed in help option name.')

        if self._hopts:
            self[self._hopts[0]] = False
            self[self._hopts[0]].desc = 'Show help message and exit.'
            for hopt in self._hopts[1:]:
                self[hopt] = self[self._hopts[0]]
        return self

    def _set_prefix(self, prefix):
        """
        Set the option prefix
        @params:
            `prefix`: The prefix
        """
        if prefix not in ('-', '--', 'auto'):
            raise ParamsParseError('Prefix should be one of -, -- and auto.')
        self._props['prefix'] = prefix
        return self

    def _set_hbald(self, hbald=True):
        """
        Set if we should show help information if no arguments passed.
        @params:
            `hbald`: The flag. show if True else hide. Default: `True`
        """
        self._props['hbald'] = hbald
        return self

    def _prefixit(self, name):
        if self._prefix == 'auto':
            return '-%s' % name if len(name.split('.')[0]) <= 1 \
                                else '--%s' % name
        return self._prefix + name

    def __contains__(self, name):
        return name in self._params

    def __repr__(self):
        return '<Params({}) @ {}>'.format(','.join(
            '{name}:{p.value!r}'.format(name=key, p=param)
            for key, param in self._params.items()
        ), hex(id(self)))

    def _all_flags(self, optname):
        """See if it all flag option in the option name"""
        optnames = list(optname)
        # flags should not be repeated
        if len(optnames) != len(set(optnames)):
            return False
        for opt in optnames:
            if opt not in self._params or self._params[opt].type != 'bool:':
                return False
        return True

    def _preparse_option_candidate(self, arg, parsed, pendings, lastopt):
        # --abc.x:list
        # abc.x:list
        argnoprefix = arg.lstrip('-')
        # abc
        argoptname = re.split(r'[.:=]', argnoprefix)[0]
        # --
        argprefix = arg[:-len(argnoprefix)] if argnoprefix else arg

        # impossible an option
        # ---a
        # self.prefix == '-'    : --abc
        # self.prefix == '--'   : -abc
        # self.prefix == 'auto' : --a
        if (len(argprefix) > 2 or
                (self._prefix + argprefix == '---') or
                (self._prefix == 'auto' and
                 argprefix == '--' and
                 len(argoptname) <= 1)):
            return self._preparse_value_candidate(arg, pendings, lastopt)

        # if a, b and c are defined as bool types, then it should be parsed as
        #  {'a': True, 'b': True, 'c': True} like '-a -b -c'
        #	# in the case '-abc' with self._prefix == '-'
        #	# 'abc' is not defined
        # pylint: disable=too-many-boolean-expressions
        if ((self._prefix in ('auto', '-') and
             argprefix == '-' and len(argoptname) > 1) and
                (self._prefix != '-' or argoptname not in self._params) and
                '=' not in argnoprefix):
            # -abc:bool
            if ((':' not in argnoprefix or
                 argnoprefix.endswith(':bool')) and
                    self._all_flags(argoptname)):
                for opt in list(argoptname):
                    parsed[opt] = self._params[opt]
                    parsed[opt].push(True, 'bool:')
                return None
            # see if -abc can be parsed as '-a bc'
            # -a. will also be parsed as '-a .' if a is not defined as dict
            #   otherwise it will be parsed as {'a': {'': ...}}
            # -a1:int is also allowed
            if (argoptname[0] in self._params and
                    (argoptname[1] != '.' or
                     self._params[argoptname[0]].type != 'dict:')):
                argname = argoptname[0]
                argval = argoptname[1:]
                argtype = argnoprefix.split(':', 1)[1] \
                          if ':' in argnoprefix \
                          else True
                parsed[argname] = self._params[argname]
                parsed[argname].push(argval, argtype)
                return None

            if (self._prefix == 'auto' and
                    argprefix == '-' and
                    len(argoptname) > 1):
                return self._preparse_value_candidate(arg, pendings, lastopt)

        matches = re.match(OPT_PATTERN, argnoprefix)
        if not matches:
            return self._preparse_value_candidate(arg, pendings, lastopt)
        argname = matches.group(1) or OPT_POSITIONAL_NAME
        argtype = matches.group(2)
        argval = matches.group(3) or OPT_UNSET_VALUE

        if argname not in parsed:
            lastopt = parsed[argname] = self._params[argname] \
                                        if argname in self._params \
                                        else Param(argname, []) \
                                        if (argname == OPT_POSITIONAL_NAME and
                                            not argtype) \
                                        else Param(argname)

        lastopt = parsed[argname]
        lastopt.push(argval, argtype or True)

        if '.' in argname:
            doptname = argname.split('.')[0]
            if doptname in parsed:
                dictopt = parsed[doptname]
            else:
                dictopt = self._params[doptname] \
                          if doptname in self._params \
                          else Param(doptname, {})
                parsed[doptname] = dictopt
            dictopt.push(lastopt, 'dict:')
        return lastopt

    @classmethod
    def _preparse_value_candidate(cls, arg, pendings, lastopt):
        if lastopt:
            lastopt.push(arg)
        else:
            pendings.append(arg)
        return lastopt

    def _preparse(self, args):
        """
        Parse the arguments from command line
        Don't coerce the types and values yet.
        """
        parsed = OrderedDict()
        pendings = []
        lastopt = None

        for arg in args:
            lastopt = self._preparse_option_candidate(arg,
                                                      parsed,
                                                      pendings,
                                                      lastopt) \
                      if arg.startswith('-') \
                      else self._preparse_value_candidate(arg,
                                                          pendings,
                                                          lastopt)
        # no options detected at all
        # all pendings will be used as positional
        if lastopt is None and pendings:
            if OPT_POSITIONAL_NAME not in parsed:
                parsed[
                    OPT_POSITIONAL_NAME
                ] = self._params[OPT_POSITIONAL_NAME] \
                    if OPT_POSITIONAL_NAME in self._params \
                    else Param(OPT_POSITIONAL_NAME, [])
            for pend in pendings:
                parsed[OPT_POSITIONAL_NAME].push(pend)
            pendings = []
        elif lastopt is not None:
            # lastopt is not list, so use the values pushed as positional
            posvalues = []
            if (not lastopt.stacks or
                    lastopt.stacks[-1][0].startswith('list:') or
                    len(lastopt.stacks[-1][1]) < 2):
                posvalues = []
            elif (lastopt.stacks[-1][0] == 'bool:' and
                  lastopt.stacks[-1][1] and
                  not re.match(OPT_BOOL_PATTERN, lastopt.stacks[-1][1][0])):
                posvalues = lastopt.stacks[-1][1]
                lastopt.stacks[-1] = (lastopt.stacks[-1][0], [])
            else:
                posvalues = lastopt.stacks[-1][1][1:]
                lastopt.stacks[-1] = (lastopt.stacks[-1][0],
                                      lastopt.stacks[-1][1][:1])

            # is it necessary to create positional? or it exists
            # or it is already there
            # if it is already there,
            # that means tailing values should not be added to positional

            if OPT_POSITIONAL_NAME in parsed or not posvalues:
                pendings.extend(posvalues)
                return parsed, pendings

            parsed[
                OPT_POSITIONAL_NAME
            ] = self._params[OPT_POSITIONAL_NAME] \
                if OPT_POSITIONAL_NAME in self._params \
                else Param(OPT_POSITIONAL_NAME, [])
            for posval in posvalues:
                parsed[OPT_POSITIONAL_NAME].push(posval)
        return parsed, pendings

    def _parse(self, # pylint: disable=too-many-branches
               args=None,
               arbi=False,
               dict_wrapper=builtins.dict,
               raise_exc=False):
        # verbose option is not allowed for prefix '--'
        if self._prefix == '--':
            for param in self._params.values():
                if param.type == 'verbose:':
                    raise ParamTypeError(
                        "Verbose option %r is not allow "
                        "with prefix '--'" % param.name
                    )

        args = sys.argv[1:] if args is None else args
        try:
            if not args and self._hbald and not arbi:
                raise ParamsParseError('__help__')
            parsed, pendings = self._preparse(args)
            warns = ['Unrecognized value: %r' % pend for pend in pendings]
            # check out dict options first
            for name, param in parsed.items():
                if '.' in name:
                    warns.extend(param.checkout())
            for name, param in parsed.items():
                if '.' in name:
                    continue
                if name in self._hopts:
                    raise ParamsParseError('__help__')
                if name in self._params:
                    pass
                elif arbi:
                    self._params[name] = param
                elif name != OPT_POSITIONAL_NAME:
                    warns.append(
                        'Unrecognized option: %r' % self._prefixit(name)
                    )
                    continue
                else:
                    warns.append(
                        'Unrecognized positional values: %s' % ', '.join(
                            repr(val) for val in param.stacks[-1][-1]
                        )
                    )
                    continue

                warns.extend(param.checkout())

            # apply callbacks
            for name, param in self._params.items():
                if not callable(param.callback):
                    continue
                try:
                    ret = param.callback(param)
                except TypeError as ex: # wrong # arguments
                    if 'missing' not in str(ex) and 'argument' not in str(ex):
                        raise
                    ret = param.callback(param, self)
                if ret is True or ret is None or isinstance(ret, Param):
                    continue

                error = 'Callback error.' if ret is False else ret
                raise ParamsParseError('Option %r: %s' % (
                    self._prefixit(name), error
                ))
            # check required
            for name, param in self._params.items():
                if (param.required and
                        param.value is None and
                        param.type != 'NoneType:'):
                    if name == OPT_POSITIONAL_NAME:
                        raise ParamsParseError(
                            'POSITIONAL option is required.'
                        )
                    raise ParamsParseError(
                        'Option %r is required.' % (self._prefixit(name))
                    )

            for warn in warns[:(MAX_WARNINGS+1)]:
                sys.stderr.write(self._assembler.warning(warn) + '\n')

            return self._as_dict(dict_wrapper)
        except ParamsParseError as exc:
            if raise_exc:
                raise
            exc = '' if str(exc) == '__help__' else str(exc)
            self._help(exc, print_and_exit=True)

    @property
    def _helpitems(self): # pylint:disable=too-many-branches
        # collect aliases
        required_params = {}
        optional_params = {}
        for name, param in self._params.items():
            if not param.show or name in self._hopts + [OPT_POSITIONAL_NAME]:
                continue
            if param.required:
                required_params.setdefault(param, []).append(name)
                continue
            optional_params.setdefault(param, []).append(name)

        # positional option
        pos_option = None
        if OPT_POSITIONAL_NAME in self._params:
            pos_option = self._params[OPT_POSITIONAL_NAME]

        helps = Helps()
        # DESCRIPTION
        if self._desc:
            helps.add('DESCRIPTION', self._desc)

        # USAGE
        helps.add('USAGE', HelpItems())
        # auto wrap long lines in usage
        # allow 2 {prog}s
        maxusagelen = MAX_PAGE_WIDTH - (len(self._prog.split()[0]) - 6)*2 - 10
        if self._usage:
            helps['USAGE'].add(sum(
                # allow 2 program names with more than 6 chars each in one usage
                # 10 chars for backup.
                (wraptext(usage,
                          maxusagelen,
                          subsequent_indent='  ')
                 for usage in self._props['usage']),
                []
            ))
        else: # default usage
            defusage = ['{prog}']
            defusage.extend('<{} {}>'.format(
                self._prefixit(names[0]),
                (param.type.rstrip(':') or names[0]).upper()
            ) for param, names in required_params.items())
            defusage.append('[OPTIONS]')

            if pos_option:
                defusage.append('POSITIONAL' \
                                if pos_option.required \
                                else '[POSITIONAL]')

            defusage = wraptext(' '.join(defusage),
                                maxusagelen,
                                subsequent_indent='  ')
            helps['USAGE'].add(defusage)

        helps.add(REQUIRED_OPT_TITLE, HelpOptions(prefix=self._prefix))
        helps.add(OPTIONAL_OPT_TITLE, HelpOptions(prefix=self._prefix))

        for param, names in required_params.items():
            helps[REQUIRED_OPT_TITLE].add_param(param, names)

        for param, names in optional_params.items():
            helps[OPTIONAL_OPT_TITLE].add_param(param, names)

        helps[OPTIONAL_OPT_TITLE].add(self._params[self._hopts[0]],
                                      self._hopts,
                                      ishelp=True)

        if pos_option:
            helpsection = helps[REQUIRED_OPT_TITLE] \
                          if pos_option.required \
                          else helps[OPTIONAL_OPT_TITLE]
            if helpsection:
                # leave an empty line for positional
                helpsection.add(('', '', ['']))
            helpsection.add_param(pos_option)

        if callable(self._helpx):
            self._helpx(helps)

        return helps

    def _help(self, error='', print_and_exit=False):
        """
        Calculate the help page
        @params:
            `error`: The error message to show before the help information.
                Default: `''`
            `print_and_exit`: Print the help page and exit the program?
                Default: `False` (return the help information)
        @return:
            The help information
        """
        assert error or isinstance(error, (list, str))

        ret = []
        if error:
            if isinstance(error, str):
                error = error.splitlines()
            ret = [self._assembler.error(err.strip()) for err in error]

        ret.extend(self._assembler.assemble(self._helpitems))

        if print_and_exit:
            sys.stderr.write('\n'.join(ret))
            sys.exit(1)
        else:
            return '\n'.join(ret)

    def _load_dict(self, dict_var, show=False):
        """
        Load parameters from a dict
        @params:
            `dict_var`: The dict variable.
            - Properties are set by "<param>.required", "<param>.show", ...
            `show`: Whether these parameters should be shown in help information
                - Default: False
                  (don'typename show parameter from config object in help page)
                - It'll be overwritten by the `show`
                    property inside dict variable.
                - If it is None, will inherit the param's show value
        """
        # pylint: disable=too-many-branches
        # load the params first
        for key, val in dict_var.items():
            if '.' in key:
                continue
            if key not in self._params:
                self._params[key] = Param(key, val)
            self._params[key].value = val
            if show is not None:
                self._params[key].show = show
        # load the params that is not given a value
        # start with setting an attribute
        for key, val in dict_var.items():
            if '.' not in key or key.endswith('.alias'):
                continue
            key = key.split('.')[0]
            if key in self._params:
                continue
            self[key] = Param(key)
            if show is not None:
                self[key].show = show
        # load aliases
        for key, val in dict_var.items():
            if not key.endswith('.alias'):
                continue
            key = key[:-6]
            if val not in self._params:
                raise ParamsLoadError(
                    'Cannot set alias %r to an undefined '
                    'option %r' % (key, val)
                )
            self[key] = self[val]
        # then load property
        for key, val in dict_var.items():
            if '.' not in key or key.endswith('.alias'):
                continue
            opt, prop = key.split('.', 1)
            if not prop in ('desc', 'required', 'show', 'type', 'value'):
                raise ParamsLoadError('Unknown attribute %r for '
                                      'option %r' % (prop, opt))
            setattr(self[opt], prop, val)
        return self

    def _load_file(self, cfgfile, profile=False, show=False):
        """
        Load parameters from a json/config file
        If the file name ends with '.json', `json.load` will be used,
        otherwise, `ConfigParser` will be used.
        For config file other than json, a section name is needed,
        whatever it is.
        @params:
            `cfgfile`: The config file
            `show`: Whether these parameters should be shown in help information
                - Default: False
                  (don'typename show parameter from config file in help page)
                - It'll be overwritten by the `show` property
                    inside the config file.
        """
        config = Config(with_profile=bool(profile))
        config._load(cfgfile)
        if profile:
            config._use(profile)
        return self._load_dict(config, show=show)

    def _as_dict(self, wrapper=builtins.dict):
        """
        Convert the parameters to dict object
        @returns:
            The dict object
        """
        ret = wrapper()
        for name in self._params:
            ret[name] = self._params[name].value
        return ret

    def _add_to_completions(self,
                            completions,
                            withtype=False,
                            alias=False,
                            showonly=True):
        revparams = OrderedDict()
        for name, param in self._params.items():
            if name in self._hopts or (showonly and not param.show):
                continue
            revparams.setdefault(param, []).append(name)
        for param, names in revparams.items():
            if not alias: # keep the longest one
                names = [list(sorted(names, key=len))[-1]]
            names = ['' if name == OPT_POSITIONAL_NAME else name
                     for name in names]
            if withtype:
                names.extend([name + ':' + param.type.rstrip(':')
                              for name in names
                              if param.type and param.type != 'auto'])
            completions.add_option([self._prefixit(name) for name in names],
                                   param.desc[0] if param.desc else '')
            if param.type == 'verbose:':
                completions.add_option(['-' + param.name * 2,
                                        '-' + param.name * 3],
                                       param.desc[0] if param.desc else '')

    def _complete(self, # pylint: disable=too-many-arguments
                  shell,
                  auto=False,
                  withtype=False,
                  alias=False,
                  showonly=True):
        from completions import Completions
        completions = Completions(desc=self._desc[0] if self._desc else '')
        self._add_to_completions(completions, withtype, alias, showonly)

        return completions.generate(shell, auto)

    _dict = _as_dict
    _load = _load_dict
