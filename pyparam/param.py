"""Parameter definition"""
import re
import builtins
import ast
from collections import OrderedDict
from .utils import _Valuable
from .defaults import (DEFAULTS,
                       OPT_UNSET_VALUE,
                       OPT_ALLOWED_TYPES,
                       OPT_TYPE_MAPPINGS,
                       OPT_NONE_PATTERN,
                       OPT_NONES,
                       OPT_INT_PATTERN,
                       OPT_FLOAT_PATTERN,
                       OPT_BOOL_PATTERN,
                       OPT_PY_PATTERN,
                       OPT_BOOL_TRUES,
                       OPT_BOOL_FALSES)

class ParamNameError(Exception):
    """Exception to raise while name of a param is invalid"""

class ParamTypeError(Exception):
    """Exception to raise while type of a param is invalid"""

class Param(_Valuable):
    """
    The class for a single parameter
    """
    # pylint: disable=too-many-instance-attributes
    def __init__(self, name, value=OPT_UNSET_VALUE):
        """
        Constructor
        @params:
            `name`:  The name of the parameter
            `value`: The initial value of the parameter
        """
        self._value, self._type = Param._type_from_value(value)

        self._desc = []
        self._required = False
        self.show = True
        self.name = name
        self.default = self._value
        self.stacks = []
        self.callback = None
        # should I raise an error if the parameters are locked?
        self._should_raise = False

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
    def _type_from_value(value):
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
            value = None
        return value, Param._normalize_type(typename)

    @staticmethod
    def _normalize_type(typename):
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
    def _dict_update(dorig, dup):
        for key, val in dup.items():
            if isinstance(val, dict):
                dorig[key] = Param._dict_update(dorig.get(key, {}), val)
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

    def push(self, value=OPT_UNSET_VALUE, typename=None):
        """
        Push the value to the stack.
        """
        # pylint: disable=too-many-branches
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
            typename = Param._normalize_type(typename)
            type1, type2 = typename.split(':')

            # no values pushed yet, push one anyway
            if not self.stacks:
                # try to push [[]] if typename is 'list:list' or
                # typename is 'reset' and self.type is list:list
                if typename == 'list:list':
                    if origtype == typename and self.value and self.value[0]:
                        # we don't need to forceType
                        # because list:list can't be deducted from value
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
                self.push(value, typename=True)
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
            self._value = Param._force_type(value, typename)
        elif type1 in ('bool', 'auto') and not value:
            self._value = True
        elif type1 == 'dict':
            if not value:
                self._value = {}
            else:
                val0 = value.pop(0)
                val0 = val0.dict() if isinstance(val0, Param) else val0
                for val in value:
                    if isinstance(val, Param):
                        val = val.dict()
                    val0 = Param._dict_update(val0, val)
                self._value = val0
        else:
            if type1 == 'verbose' and not value:
                value.append(1)
            self._value = Param._force_type(value.pop(0), typename, self.name)
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
        if self._should_raise:
            raise ParamNameError(
                "Try to change a hiden parameter in locked parameters."
            )
        self._value = value
        self.default = value

    @property
    def desc(self):
        """Return the description of a param"""
        # try to add default value information in desc
        self._desc = self._desc or ['']
        self._desc[-1] = self._desc[-1].rstrip()

        #  add default only if
        # 1. not self.required
        # 2. self.required and self.value is not None
        # 3. default not in any _desc
        if not self.required or self.default is not None:
            found_default = False
            indent_index = None
            for i, desc in enumerate(self._desc):
                if any(default in desc for default in DEFAULTS):
                    found_default = True
                if len(desc.lstrip()) < len(desc):
                    indent_index = i
            indent_index = -1 if indent_index is None else indent_index - 1

            if not found_default:
                default = 'Default: %r' % self.default
                # insert default before the first indent desc line
                if len(self._desc) == 1 and not self._desc[0]:
                    self._desc = [default]
                elif self._desc[indent_index][-1:] == ' ':
                    self._desc[indent_index] += default
                else:
                    self._desc[indent_index] += ' ' + default
        if len(self._desc) == 1 and not self._desc[-1]:
            self._desc[-1] = '[No description]'

        return self._desc

    @desc.setter
    def desc(self, desc):
        if self._should_raise:
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
        if self._should_raise:
            raise ParamNameError(
                "Try to change a hiden parameter in locked parameters."
            )
        if self.type == 'bool:':
            raise ParamTypeError(
                self.value,
                'Bool option %r cannot be set as required' % self.name
            )
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
        if self._should_raise:
            raise ParamNameError(
                "Try to change a hiden parameter in locked parameters."
            )
        self.set_type(typename, True)

    @staticmethod
    def _force_type(value, typename, name=None):
        # pylint: disable=too-many-branches,too-many-return-statements
        if not typename:
            return value
        type1, type2 = typename.split(':', 1)
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
                    return Param._force_type(value,
                                             Param._normalize_type(typename))
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
                type2 = Param._normalize_type(type2)
                return [Param._force_type(x, type2) for x in value]

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

    def set_desc(self, desc):
        """
        Set the description of the parameter
        @params:
            `desc`: The description
        """
        self.desc = desc
        return self

    def set_required(self, req=True):
        """
        Set whether this parameter is required
        @params:
            `req`: True if required else False. Default: True
        """
        self.required = req
        return self

    def set_type(self, typename, update_value=True):
        """
        Set the type of the parameter
        @params:
            `typename`: The type of the value. Default: str
            - Note: str rather then 'str'
        """
        if not isinstance(typename, str):
            typename = typename.__name__
        self._type = Param._normalize_type(typename)
        # verbose type can only have name with length 1
        if self._type == 'verbose:' and len(self.name) != 1:
            raise ParamTypeError(
                "Option with type 'verbose' can only have name with length 1."
            )
        if update_value:
            self._value = Param._force_type(self.value, self._type)
        return self

    def set_callback(self, callback):
        """
        Set callback
        @params:
            `callback`: The callback
        """
        if self._should_raise:
            raise ParamNameError(
                "Try to change a hiden parameter in locked parameters."
            )
        if callback and not callable(callback):
            raise TypeError('Callback is not callable.')
        self.callback = callback
        return self

    def set_show(self, show=True):
        """
        Set whether this parameter should be shown in help information
        @params:
            `show`: True if it shows else False. Default: True
        """
        self.show = show
        return self

    def set_value(self, value, update_type=False):
        """
        Set the value of the parameter.
        Note default value will be not updated
        @params:
            `val`: The value
        """
        if update_type:
            self._value, self._type = Param._type_from_value(value)
        else:
            self._value = value
        return self
