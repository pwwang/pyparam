"""Params for pyparam"""

import sys
import re
import ast
import builtins
from os import path
from collections import OrderedDict
from simpleconf import Config
from .help import (HelpItems,
                   HelpOptions,
                   Helps,
                   HelpAssembler)
from .utils import _Valuable, _Hashable, wraptext
from .defaults import (OPT_UNSET_VALUE,
                       OPT_ALLOWED_TYPES,
                       OPT_TYPE_MAPPINGS,
                       OPT_POSITIONAL_NAME,
                       OPT_NONE_PATTERN,
                       OPT_NONES,
                       OPT_INT_PATTERN,
                       OPT_FLOAT_PATTERN,
                       OPT_BOOL_PATTERN,
                       OPT_PY_PATTERN,
                       OPT_BOOL_TRUES,
                       OPT_BOOL_FALSES,
                       OPT_PATTERN,
                       REQUIRED_OPT_TITLE,
                       OPTIONAL_OPT_TITLE,
                       MAX_WARNINGS,
                       MAX_PAGE_WIDTH)

class ParamNameError(Exception):
    """Exception to raise while name of a param is invalid"""

class ParamTypeError(Exception):
    """Exception to raise while type of a param is invalid"""

class ParamsParseError(Exception):
    """Exception to raise while failed to parse arguments from command line"""

class ParamsLoadError(Exception):
    """Exception to raise while failed to load params from dict/file"""


class Param(_Valuable):
    """
    The class for a single parameter
    """
    def __init__(self, name, value=OPT_UNSET_VALUE):
        """
        Constructor
        @params:
            `name`:  The name of the parameter
            `value`: The initial value of the parameter
        """
        self._value, self._type = Param._typeFromValue(value)

        self._desc     = []
        self._required = False
        self.show      = True
        self.name      = name
        self.default   = self._value
        self.stacks    = []
        self.callback  = None
        # should I raise an error if the parameters are locked?
        self._shouldRaise = False

        # We cannot change name later on
        if not isinstance(name, str):
            raise ParamNameError(name, 'Not a string')
        if not re.search(r'^[A-Za-z0-9_,\-.]{1,255}$', name):
            raise ParamNameError(
                name,
                'Expect a string with comma, alphabetics '
                'and/or underlines in length 1~255, but we got'
            )

    @staticmethod
    def _typeFromValue(value):
        typename = type(value).__name__
        if isinstance(value, (tuple, set)):
            typename = 'list'
            value = list(value)
        # dict could have a lot of subclasses
        elif isinstance(value, (Param, dict)):
            typename = 'dict'
        elif value != OPT_UNSET_VALUE:
            if typename not in OPT_ALLOWED_TYPES:
                raise ParamTypeError('Type not allowed: %r' % typename)
        else:
            typename = 'auto'
            value    = None
        return value, Param._normalizeType(typename)

    @staticmethod
    def _normalizeType(typename):
        if typename is None:
            return None
        if not isinstance(typename, str):
            typename = typename.__name__
        type1, type2 = (typename.rstrip(':') + ':').split(':')[:2]
        type1 = OPT_TYPE_MAPPINGS.get(type1, type1)
        type2 = OPT_TYPE_MAPPINGS.get(type2, type2)
        if type1 == 'reset' and type2:
            raise ParamTypeError("Subtype not allowed for 'reset'")
        if type1 == 'dict' and type2 and type2 != 'reset':
            raise ParamTypeError("Only allowed subtype 'reset' for 'dict'")
        if type2 == 'list' and type1 != 'list':
            raise ParamTypeError("Subtype 'list' of only allow for 'list'")
        if type2 and type1 not in ('list', 'dict'):
            raise ParamTypeError(
                'Subtype %r is only allowed for list and dict' % type2
            )
        # make sure split returns 2 elements, even if type2 == ''
        return '%s:%s' % (type1, type2)

    @staticmethod
    def _dictUpdate(dorig, dup):
        for key, val in dup.items():
            if isinstance(val, dict):
                dorig[key] = Param._dictUpdate(dorig.get(key, {}), val)
            else:
                dorig[key] = val
        return dorig

    # this will set to None if __eq__ is overwritten
    def __hash__(self):
        """
        Use id as identifier for hash
        """
        return id(self)

    def __eq__(self, other):
        if isinstance(other, Param):
            return (self.value == other.value and
                    (not self.type or
                     not other.type or
                     self.type == other.type))
        return self.value == other

    def push(self, value = OPT_UNSET_VALUE, typename = None):
        """
        Push the value to the stack.
        """
        # nothing to do, no self.type, no typename and no value
        if (typename is None and
                value == OPT_UNSET_VALUE and
                self.type == 'auto:'):
            return

        # push an item forcely using previous type
        # in case the option is give by '-a 1' without any type specification
        # if no type specified, deduct from the value
        # otherwise auto
        origtype = self.stacks[-1][0] if self.stacks else self.type

        typename = origtype if typename is True else typename
        # if typename is give, push a tuple anyway unless
        # type1 == 'list:' and type2 != 'reset'
        # type1 == 'dict:' and type2 != 'reset'
        if typename:
            # normalize type and get primary and secondary type
            typename = Param._normalizeType(typename)
            type1, type2 = typename.split(':')

            # no values pushed yet, push one anyway
            if not self.stacks:
                # try to push [[]] if typename is 'list:list' or
                # typename is 'reset' and self.type is list:list
                if typename == 'list:list':
                    if origtype == typename and self.value and self.value[0]:
                        # we don't need to forceType because list:list can't be deducted from value
                        self.stacks.append((typename, self.value[:] + [[]]))
                    else:
                        self.stacks.append((typename, [[]]))
                elif type1 == 'reset':
                    self.stacks.append((origtype, [[]] \
                                        if origtype == 'list:list' \
                                        else []))
                elif type2 == 'reset':
                    self.stacks.append((type1 + ':', []))
                elif type1 == 'list':
                    self.stacks.append((
                        typename,
                        (self.value or [])[:] if origtype == typename else []
                    ))
                elif type1 == 'dict':
                    self.stacks.append((
                        typename,
                        [(self.value or {}).copy()] \
                            if origtype == typename \
                            else []
                    ))
                else:
                    self.stacks.append((typename, []))
            elif type2 == 'reset':
                # no warnings, reset is intended
                self.stacks[-1] = (origtype, [])
            elif type1 == 'reset':
                if origtype == 'list:list':
                    # no warnings, reset is intended
                    self.stacks = [(origtype, [[]])]
                else:
                    self.stacks = [(origtype, [])]
            elif type2 == 'list':
                if origtype == 'list:list':
                    self.stacks[-1][-1].append([])
                else:
                    self.stacks.append((typename, [[]]))
            elif type1 not in ('list', 'dict'):
                self.stacks.append((typename, []))
            elif (type1 == 'list' and
                    origtype != typename and
                    not self.stacks[-1][-1]):
                # previous is reset
                self.stacks[-1] = (typename, [])

            # since container has been created
            self.push(value)
        else:
            if not self.stacks:
                self.push(value, typename = True)
            elif value != OPT_UNSET_VALUE:
                type2 = origtype.split(':')[1]
                prevalue = self.stacks[-1][-1][-1] \
                           if type2 == 'list' \
                           else self.stacks[-1][-1]
                prevalue.append(value)

    def checkout(self):
        """Checkout the types and values in stack"""
        # use self._value = value instead of self.value = value
        # don't update default
        if not self.stacks:
            return []

        typename, value = self.stacks.pop(-1)
        warns = ['Previous settings (type=%r, value=%r) '
                 'were ignored for option %r' % (
                     wtype, wval, self.name
                 ) for wtype, wval in self.stacks]
        self.stacks = []

        type1, type2 = typename.split(':')
        self._type = typename
        if type2 == 'list':
            self._value = value
        elif type1 == 'list':
            self._value = Param._forceType(value, typename)
        elif type1 in ('bool', 'auto') and not value:
            self._value = True
        elif type1 == 'dict':
            if not value:
                self._value = {}
            else:
                val0 = value.pop(0)
                if isinstance(val0, Param):
                    val0 = val0.dict()
                for val in value:
                    if isinstance(val, Param):
                        val = val.dict()
                    val0 = Param._dictUpdate(val0, val)
                self._value = val0
        else:
            if type1 == 'verbose' and not value:
                value.append(1)
            self._value = Param._forceType(value.pop(0), typename, self.name)
            for val in value:
                warns.append(
                    'Later value %r was ignored for option %r (type=%r)' % (
                        val, self.name, typename
                    )
                )

        return warns

    @property
    def value(self):
        """Get the value of the parameter"""
        return self._value

    @value.setter
    def value(self, value):
        if self._shouldRaise:
            raise ParamNameError(
                "Try to change a hiden parameter in locked parameters."
            )
        self._value = value
        self.default = value

    @property
    def desc(self):
        """Return the description of a param"""
        # try to add default value information in desc
        self._desc = self._desc or []
        if not self._desc:
            self._desc.append('')
        self._desc[-1] = self._desc[-1].rstrip()
        #  add default only if
        # 1. not self.required
        # 2. self.required and self.value is not None
        # 3. default not in self._desc[-1]
        if not ('DEFAULT: ' in self._desc[-1] or
                'Default: ' in self._desc[-1] or
                (self.required and self.default is None)):
            if len(self._desc[-1]) > 20:
                self._desc.append('Default: %r' % self.default)
            else:
                self._desc[-1] = self._desc[-1] and self._desc[-1] + ' '
                self._desc[-1] = self._desc[-1] + 'Default: %r' % self.default

        if len(self._desc) == 1 and not self._desc[-1]:
            self._desc[-1] = '[No description]'
        return self._desc

    @desc.setter
    def desc(self, desc):
        if self._shouldRaise:
            raise ParamNameError(
                "Try to change a hiden parameter in locked parameters."
            )
        assert isinstance(desc, (list, str))
        self._desc = desc if isinstance(desc, list) else desc.splitlines()

    @property
    def required(self):
        """Return if the param is required"""
        return self._required

    @required.setter
    def required(self, req):
        if self._shouldRaise:
            raise ParamNameError(
                "Try to change a hiden parameter in locked parameters."
            )
        if self.type == 'bool:':
            raise ParamTypeError(
                self.value, 'Bool option %r cannot be set as required' % self.name)
        # try remove default: in desc if self.value is None
        if self._desc and self._desc[-1].endswith('Default: None'):
            self._desc[-1] = self._desc[-1][:-13].rstrip()
        self._required = req

    @property
    def type(self):
        """Return the type of the param"""
        return self._type

    @type.setter
    def type(self, typename):
        if self._shouldRaise:
            raise ParamNameError(
                "Try to change a hiden parameter in locked parameters."
            )
        self.setType(typename, True)

    @staticmethod
    def _forceType(value, typename, name=None): # pylint: disable=too-many-branches
        if not typename:
            return value
        type1, type2 = typename.split(':')
        try:
            if type1 in ('int', 'float', 'str'):
                if value is None:
                    return None
                return getattr(builtins, type1)(value)

            if type1 == 'verbose':
                if value is None:
                    return 0
                if value == '':
                    return 1
                if (isinstance(value, (int, float)) or
                        (isinstance(value, str) and value.isdigit())):
                    return int(value)
                if isinstance(value, str) and value.count(name) == len(value):
                    return len(value) + 1
                raise ParamTypeError(
                    'Unable to coerce value %r to verbose (int)' % value
                )

            if type1 == 'bool':
                if value in OPT_BOOL_TRUES:
                    return True
                if value in OPT_BOOL_FALSES:
                    return False
                raise ParamTypeError(
                    'Unable to coerce value %r to bool' % value
                )

            if type1 == 'NoneType':
                if not value in OPT_NONES:
                    raise ParamTypeError(
                        'Unexpected value %r for NoneType' % value
                    )
                return None

            if type1 == 'py':
                if value is None:
                    return None
                value = value[3:] if value.startswith('py:') \
                                  else value[5:] \
                                  if value.startswith('repr:') \
                                  else value
                return ast.literal_eval(value)

            if type1 == 'dict':
                if value is None:
                    return None
                if not isinstance(value, dict):
                    value = value or {}
                    try:
                        value = dict(value)
                    except TypeError:
                        raise ParamTypeError(
                            'Cannot coerce %r to dict.' % value
                        )
                return OrderedDict(value.items())

            if type1 == 'auto':
                try:
                    typename = 'NoneType' \
                        if re.match(OPT_NONE_PATTERN, value) \
                        else 'int' \
                        if re.match(OPT_INT_PATTERN, value) \
                        else 'float' \
                        if re.match(OPT_FLOAT_PATTERN, value) \
                        else 'bool' \
                        if re.match(OPT_BOOL_PATTERN, value) \
                        else 'py' \
                        if re.match(OPT_PY_PATTERN, value) \
                        else 'str'
                    return Param._forceType(value,
                                            Param._normalizeType(typename))
                except TypeError: # value is not a string, cannot do re.match
                    return value

            if type1 == 'list':
                if value is None:
                    return None
                type2 = type2 or 'auto'
                if isinstance(value, str):
                    value = [value]
                try:
                    value = list(value)
                except TypeError:
                    value = [value]
                if type2 == 'reset':
                    return value
                if type2 == 'list':
                    return value if value and isinstance(value[0], list) \
                                 else [value]
                type2 = Param._normalizeType(type2)
                return [Param._forceType(x, type2) for x in value]

            raise TypeError
        except (ValueError, TypeError):
            raise ParamTypeError(
                'Unable to coerce value %r to type %r' % (value, typename)
            )

    def dict(self):
        """
        Return the value in dict format
        There must be dot('.') in the name
        The first part will be ignored
        params a.b.c with value 1 will be converted into
        {"b": {"c": 1}}
        """
        if '.' not in self.name:
            raise ParamTypeError('Unable to convert param into dict '
                                 'without dot in name: %r' % self.name)
        ret0 = ret = {}
        parts = self.name.split('.')
        for part in parts[1:-1]:
            ret[part] = {}
            ret = ret[part]
        ret[parts[-1]] = self.value
        return ret0

    def __repr__(self):
        typename = self.type or ''
        return ('<Param(name={!r},value={!r},type={!r},required={!r},'
                'show={!r}) @ {}>').format(self.name,
                                           self.value,
                                           typename.rstrip(':'),
                                           self.required,
                                           self.show,
                                           hex(id(self)))

    def setDesc(self, desc):
        """
        Set the description of the parameter
        @params:
            `desc`: The description
        """
        self.desc = desc
        return self

    def setRequired(self, req=True):
        """
        Set whether this parameter is required
        @params:
            `req`: True if required else False. Default: True
        """
        self.required = req
        return self

    def setType(self, typename, update_value=True):
        """
        Set the type of the parameter
        @params:
            `typename`: The type of the value. Default: str
            - Note: str rather then 'str'
        """
        if not isinstance(typename, str):
            typename = typename.__name__
        self._type = Param._normalizeType(typename)
        # verbose type can only have name with length 1
        if self._type == 'verbose:' and len(self.name) != 1:
            raise ParamTypeError(
                "Option with type 'verbose' can only have name with length 1."
            )
        if update_value:
            self._value = Param._forceType(self.value, self._type)
        return self

    def setCallback(self, callback):
        """
        Set callback
        @params:
            `callback`: The callback
        """
        if self._shouldRaise:
            raise ParamNameError(
                "Try to change a hiden parameter in locked parameters."
            )
        if callback and not callable(callback):
            raise TypeError('Callback is not callable.')
        self.callback = callback
        return self

    def setShow (self, show = True):
        """
        Set whether this parameter should be shown in help information
        @params:
            `show`: True if it shows else False. Default: True
        """
        self.show = show
        return self

    def setValue(self, value, update_type=False):
        """
        Set the value of the parameter.
        Note default value will be not updated
        @params:
            `val`: The value
        """
        if update_type:
            self._value, self._type = Param._typeFromValue(value)
        else:
            self._value = value
        return self

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
            prog       = prog,
            usage      = [],
            desc       = [],
            hopts      = ['h', 'help', 'H'],
            prefix     = 'auto',
            hbald      = True,
            assembler  = HelpAssembler(prog, theme),
            helpx      = None,
            locked     = False,
            lockedkeys = []
        )
        self.__dict__['_params']    = OrderedDict()
        self._setHopts(self._hopts)

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
            getattr(self, '_set' + name[1:].capitalize())(value)
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
            self._params[name]._shouldRaise = True
        return self._params[name]

    __getitem__ = __getattr__
    __setitem__ = __setattr__

    def _setTheme(self, theme):
        """
        Set the theme
        @params:
            `theme`: The theme
        """
        self._props['assembler'] = HelpAssembler(self._prog, theme)
        return self

    def _setUsage(self, usage):
        """
        Set the usage
        @params:
            `usage`: The usage
        """
        assert isinstance(usage, (list, str))
        self._props['usage'] = usage if isinstance(usage, list) \
                                     else usage.splitlines()
        return self

    def _setDesc(self, desc):
        """
        Set the description
        @params:
            `desc`: The description
        """
        assert isinstance(desc, (list, str))
        self._props['desc'] = desc if isinstance(desc, list) \
                                   else desc.splitlines()
        return self

    def _setHopts(self, hopts):
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

    def _setPrefix(self, prefix):
        """
        Set the option prefix
        @params:
            `prefix`: The prefix
        """
        if prefix not in ('-', '--', 'auto'):
            raise ParamsParseError('Prefix should be one of -, -- and auto.')
        self._props['prefix'] = prefix
        return self

    def _prefixit(self, name):
        if self._prefix == 'auto':
            return '-%s' % name if len(name.split('.')[0]) <= 1 \
                                else '--%s' % name
        return self._prefix + name

    def __contains__(self, name):
        return name in self._params

    def _setHbald(self, hbald=True):
        """
        Set if we should show help information if no arguments passed.
        @params:
            `hbald`: The flag. show if True else hide. Default: `True`
        """
        self._props['hbald'] = hbald
        return self

    def __repr__(self):
        return '<Params({}) @ {}>'.format(','.join(
            '{name}:{p.value!r}'.format(name = key, p = param)
            for key, param in self._params.items()
        ), hex(id(self)))

    def _allFlags(self, optname):
        """See if it all flag option in the option name"""
        optnames = list(optname)
        # flags should not be repeated
        if len(optnames) != len(set(optnames)):
            return False
        for opt in optnames:
            if opt not in self._params or self._params[opt].type != 'bool:':
                return False
        return True

    def _preParseOptionCandidate(self, arg, parsed, pendings, lastopt):
        # --abc.x:list
        # abc.x:list
        argnoprefix = arg.lstrip('-')
        # abc
        argoptname  = re.split(r'[.:=]', argnoprefix)[0]
        # False
        argshort    = len(argoptname) <= 1
        # --
        argprefix   = arg[:-len(argnoprefix)] if argnoprefix else arg

        # impossible an option
        # ---a
        # self.prefix == '-'    : --abc
        # self.prefix == '--'   : -abc
        # self.prefix == 'auto' : --a
        if len(argprefix) > 2 or \
            (self._prefix == '-' and argprefix == '--') or \
            (self._prefix == '--' and argprefix == '-') or \
            (self._prefix == 'auto' and argprefix == '--' and argshort):
            return self._preParseValueCandidate(arg, pendings, lastopt)

        # if a, b and c are defined as bool types, then it should be parsed as
        #  {'a': True, 'b': True, 'c': True} like '-a -b -c'
        #	# in the case '-abc' with self._prefix == '-'
        #	# 'abc' is not defined
        if ((self._prefix in ('auto', '-') and
             argprefix == '-' and len(argoptname) > 1) and
            (self._prefix != '-' or argoptname not in self._params) and
             '=' not in argnoprefix):
            # -abc:bool
            if ((':' not in argnoprefix or
                    argnoprefix.endswith(':bool')) and
                 self._allFlags(argoptname)):
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
                argval  = argoptname[1:]
                argtype = argnoprefix.split(':', 1)[1] \
                          if ':' in argnoprefix \
                          else True
                parsed[argname] = self._params[argname]
                parsed[argname].push(argval, argtype)
                return None

            if (self._prefix == 'auto' and
                    argprefix == '-' and
                    len(argoptname) > 1):
                return self._preParseValueCandidate(arg, pendings, lastopt)

        matches = re.match(OPT_PATTERN, argnoprefix)
        if not matches:
            return self._preParseValueCandidate(arg, pendings, lastopt)
        argname = matches.group(1) or OPT_POSITIONAL_NAME
        argtype = matches.group(2)
        argval  = matches.group(3) or OPT_UNSET_VALUE

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
    def _preParseValueCandidate(cls, arg, pendings, lastopt):
        if lastopt:
            lastopt.push(arg)
        else:
            pendings.append(arg)
        return lastopt

    def _preParse(self, args):
        """
        Parse the arguments from command line
        Don't coerce the types and values yet.
        """
        parsed   = OrderedDict()
        pendings = []
        lastopt  = None

        for arg in args:
            lastopt = self._preParseOptionCandidate(arg,
                                                    parsed,
                                                    pendings,
                                                    lastopt) \
                      if arg.startswith('-') \
                      else self._preParseValueCandidate(arg,
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

    def _parse(self,
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
            parsed, pendings = self._preParse(args)
            warns  = ['Unrecognized value: %r' % pend for pend in pendings]
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

            return self._asDict(dict_wrapper)
        except ParamsParseError as exc:
            if raise_exc:
                raise
            exc = '' if str(exc) == '__help__' else str(exc)
            self._help(exc, print_and_exit = True)

    @property
    def _helpitems(self):
        # collect aliases
        required_params = {}
        optional_params = {}
        for name, param in self._params.items():
            if not param.show or name in self._hopts + [OPT_POSITIONAL_NAME]:
                continue
            if param.required:
                required_params.setdefault(param, []).append(name)
            else:
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
            helps['USAGE'].add(sum((wraptext(
                # allow 2 program names with more than 6 chars each in one usage
                # 10 chars for backup.
                usage, maxusagelen, subsequent_indent='  ')
                for usage in self._props['usage']), []))
        else: # default usage
            defusage = '{prog}'
            for param, names in required_params.items():
                defusage += ' <{} {}>'.format(
                    self._prefixit(names[0]),
                    (param.type.rstrip(':') or names[0]).upper())
            defusage += ' [OPTIONS]'

            if pos_option:
                defusage += ' POSITIONAL' if pos_option.required \
                                          else ' [POSITIONAL]'

            defusage = wraptext(defusage, maxusagelen, subsequent_indent='  ')
            helps['USAGE'].add(defusage)

        helps.add(REQUIRED_OPT_TITLE, HelpOptions(prefix=self._prefix))
        helps.add(OPTIONAL_OPT_TITLE, HelpOptions(prefix=self._prefix))

        for param, names in required_params.items():
            helps[REQUIRED_OPT_TITLE].addParam(param, names)

        for param, names in optional_params.items():
            helps[OPTIONAL_OPT_TITLE].addParam(param, names)

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
            helpsection.addParam(pos_option)

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

    def _loadDict(self, dict_var, show=False):
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
        # load the params first
        for key, val in dict_var.items():
            if '.' in key:
                continue
            if not key in self._params:
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

    def _loadFile(self, cfgfile, profile=False, show=False):
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
        return self._loadDict(config, show=show)

    def _asDict(self, wrapper=builtins.dict):
        """
        Convert the parameters to dict object
        @returns:
            The dict object
        """
        ret = wrapper()
        for name in self._params:
            ret[name] = self._params[name].value
        return ret

    def _addToCompletions(self,
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
            completions.addOption([self._prefixit(name) for name in names],
                                  param.desc[0] if param.desc else '')
            if param.type == 'verbose:':
                completions.addOption(['-' + param.name * 2,
                                       '-' + param.name * 3],
                                      param.desc[0] if param.desc else '')

    def _complete(self,
                  shell,
                  auto=False,
                  withtype=False,
                  alias=False,
                  showonly=True):
        from completions import Completions
        completions = Completions(desc=self._desc[0] if self._desc else '')
        self._addToCompletions(completions, withtype, alias, showonly)

        return completions.generate(shell, auto)

    _dict = _asDict
    _load = _loadDict
