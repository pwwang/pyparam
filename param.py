"""
parameters module for PyPPL
"""
import sys
import re
import ast
import builtins
import textwrap
from os import path
from collections import OrderedDict
import colorama
from simpleconf import Config

# the max width of the help page, not including the leading space
MAX_PAGE_WIDTH = 100
# the max width of the option name (include the type and placeholder, but not the leading space)
MAX_OPT_WIDTH  = 36
# the min gap between optname/opttype and option description
MIN_OPT_GAP    = 5
# maximum warnings to print
MAX_WARNINGS   = 10

THEMES = dict(
	default = dict(
		error   = colorama.Fore.RED,
		warning = colorama.Fore.YELLOW,
		title   = colorama.Style.BRIGHT + colorama.Fore.CYAN,  # section title
		prog    = colorama.Style.BRIGHT + colorama.Fore.GREEN, # program name
		default = colorama.Fore.MAGENTA,              # default values
		optname = colorama.Style.BRIGHT + colorama.Fore.GREEN,
		opttype = colorama.Fore.BLUE,
		optdesc = ''),

	blue = dict(
		title   = colorama.Style.BRIGHT + colorama.Fore.GREEN,
		prog    = colorama.Style.BRIGHT + colorama.Fore.BLUE,
		optname = colorama.Style.BRIGHT + colorama.Fore.BLUE,
		opttype = colorama.Style.BRIGHT),

	plain = dict(
		error   = '', warning = '', title   = '', prog    = '',
		default = '', optname = '', opttype = '')
)

OPT_ALLOWED_TYPES = ('str', 'int', 'float', 'bool', 'list', 'py', 'NoneType', 'dict')

OPT_TYPE_MAPPINGS = dict(
	a = 'auto',  auto  = 'auto',  i = 'int',   int   = 'int',  n = 'NoneType',
	f = 'float', float = 'float', b = 'bool',  bool  = 'bool', none = 'NoneType',
	s = 'str',   str   = 'str',   d = 'dict',  dict = 'dict',  box = 'dict',
	p = 'py',    py    = 'py',    python = 'py', r = 'reset',  reset = 'reset',
	l = 'list',  list  = 'list',  array  = 'list',
)

OPT_BOOL_TRUES  = [True , 1, 't', 'T', 'True' , 'TRUE' , 'true' , '1', 'Y', 'y', 'Yes',
	'YES', 'yes', 'on' , 'ON' , 'On' ]

OPT_BOOL_FALSES = [False, 0, 'f', 'F', 'False', 'FALSE', 'false', '0', 'N', 'n', 'No' ,
	'NO' , 'no' , 'off', 'OFF', 'Off', None]

OPT_NONES = [None, 'none', 'None']

OPT_PATTERN       = r"^([a-zA-Z\?@-][\w,\._-]*)?(?::([\w:]+))?(?:=(.*))?$"
OPT_INT_PATTERN   = r'^[+-]?\d+$'
OPT_FLOAT_PATTERN = r'^[+-]?(?:\d*\.)?\d+(?:[Ee][+-]\d+)?$'
OPT_NONE_PATTERN  = r'^none|None$'
OPT_BOOL_PATTERN  = r'^(t|T|True|TRUE|true|1|Y|y|Yes|YES|yes|on|ON|On|f|F|False' + \
	r'|FALSE|false|0|N|n|No|NO|off|Off|OFF|None|none)$'
OPT_PY_PATTERN    = r'^(?:py|repr):(.+)$'

OPT_POSITIONAL_NAME = '_'
OPT_UNSET_VALUE     = '__Param_Value_Not_Set__'
CMD_COMMON_PARAMS   = '_'

REQUIRED_OPT_TITLE = 'REQUIRED OPTIONS'
OPTIONAL_OPT_TITLE = 'OPTIONAL OPTIONS'

class ParamNameError(Exception):
	pass

class ParamTypeError(Exception):
	pass

class ParamsParseError(Exception):
	pass

class ParamsLoadError(Exception):
	pass

class CommandsParseError(Exception):
	pass

class _Hashable:
	"""
	A class for object that can be hashable
	"""
	def __hash__(self):
		"""
		Use id as identifier for hash
		"""
		return id(self)

	def __eq__(self, other):
		"""
		How to compare the hash keys
		"""
		return id(self) == id(other)

	def __ne__(self, other):
		"""
		Compare hash keys
		"""
		return not self.__eq__(other)

class _Valuable:

	STR_METHODS = ('capitalize', 'center', 'count', 'decode', 'encode', 'endswith', \
		'expandtabs', 'find', 'format', 'index', 'isalnum', 'isalpha', 'isdigit', \
		'islower', 'isspace', 'istitle', 'isupper', 'join', 'ljust', 'lower', 'lstrip', \
		'partition', 'replace', 'rfind', 'rindex', 'rjust', 'rpartition', 'rsplit', \
		'rstrip', 'split', 'splitlines', 'startswith', 'strip', 'swapcase', 'title', \
		'translate', 'upper', 'zfill')

	def __str__(self):
		return str(self.value)

	def str(self):
		return str(self.value)

	def int(self, raise_exc = True):
		try:
			return int(self.value)
		except (ValueError, TypeError):
			if raise_exc:
				raise
			return None

	def float(self, raise_exc = True):
		try:
			return float(self.value)
		except (ValueError, TypeError):
			if raise_exc:
				raise
			return None

	def bool(self):
		return bool(self.value)

	def __getattr__(self, item):
		# attach str methods
		if item in _Valuable.STR_METHODS:
			return getattr(str(self.value), item)
		raise AttributeError('No such attribute: {}'.format(item))

	def __add__(self, other):
		return self.value + other

	def __contains__(self, other):
		return other in self.value

	def __hash__(self): # pragma: no cover
		"""
		Use id as identifier for hash
		"""
		return id(self)

	def __eq__(self, other): # pragma: no cover
		return self.value == other

	def __ne__(self, other):
		return not self.__eq__(other)

def _textwrap(text, width = 70, **kwargs):
	width -= 2
	wraps = textwrap.wrap(text, width, **kwargs)
	return [line + ' \\' if i < len(wraps) - 1 else line
			for i, line in enumerate(wraps)]

class HelpAssembler:
	"""A helper class to help assembling the help information page."""
	def __init__(self, prog = None, theme = 'default'):
		"""
		Constructor
		@params:
			`prog`: The program name
			`theme`: The theme. Could be a name of `THEMES`, or a dict of a custom theme.
		"""
		self.progname = prog or path.basename(sys.argv[0])
		self.theme    = THEMES['default'].copy()
		if theme != 'default':
			self.theme.update(theme if isinstance(theme, dict) else THEMES[theme])

	def error(self, msg, with_prefix = True):
		"""
		Render an error message
		@params:
			`msg`: The error message
		"""
		msg = msg.format(prog = self.prog(self.progname))
		return '{colorstart}{prefix}{msg}{colorend}'.format(
			colorstart = self.theme['error'],
			prefix     = 'Error: ' if with_prefix else '',
			msg        = msg,
			colorend   = colorama.Style.RESET_ALL
		)

	def warning(self, msg, with_prefix = True):
		"""
		Render an warning message
		@params:
			`msg`: The warning message
		"""
		msg = msg.format(prog = self.prog(self.progname))
		return '{colorstart}{prefix}{msg}{colorend}'.format(
			colorstart = self.theme['warning'],
			prefix     = 'Warning: ' if with_prefix else '',
			msg        = msg,
			colorend   = colorama.Style.RESET_ALL
		)

	warn = warning

	def title(self, msg, with_colon = True):
		"""
		Render an section title
		@params:
			`msg`: The section title
		"""
		return '{colorstart}{msg}{colorend}{colon}'.format(
			colorstart = self.theme['title'],
			msg        = msg.upper(),
			colorend   = colorama.Style.RESET_ALL,
			colon      = ':' if with_colon else ''
		)

	def prog(self, prog = None):
		"""
		Render the program name
		@params:
			`msg`: The program name
		"""
		if prog is None:
			prog = self.progname
		return '{colorstart}{prog}{colorend}'.format(
			colorstart = self.theme['prog'],
			prog       = prog,
			colorend   = colorama.Style.RESET_ALL
		)

	def plain(self, msg):
		"""
		Render a plain message
		@params:
			`msg`: the message
		"""
		return msg.format(prog = self.prog(self.progname))

	def optname(self, msg, prefix = '  '):
		"""
		Render the option name
		@params:
			`msg`: The option name
		"""
		return '{colorstart}{prefix}{msg}{colorend}'.format(
			colorstart = self.theme['optname'],
			prefix     = prefix,
			msg        = msg,
			colorend   = colorama.Style.RESET_ALL
		)

	def opttype(self, msg):
		"""
		Render the option type or placeholder
		@params:
			`msg`: the option type or placeholder
		"""
		trimmedmsg = msg.rstrip().upper()
		if not trimmedmsg:
			return msg + '  '
		return '{colorstart}{msg}{colorend}'.format(
			colorstart = self.theme['opttype'],
			msg        = ('({})' if trimmedmsg == 'BOOL' else '<{}>').format(trimmedmsg),
			colorend   = colorama.Style.RESET_ALL
		) + ' ' * (len(msg) - len(trimmedmsg))

	def optdesc(self, msg, first = False):
		"""
		Render the option descriptions
		@params:
			`msg`: the option descriptions
		"""
		msg = msg.format(prog = self.prog(self.progname))

		default_index = msg.rfind('DEFAULT: ')
		if default_index == -1:
			default_index = msg.rfind('Default: ')

		if default_index != -1:
			defaults = '{colorstart}{defaults}{colorend}'.format(
				colorstart = self.theme['default'],
				defaults   = msg[default_index:],
				colorend   = colorama.Style.RESET_ALL
			)
			msg = msg[:default_index] + defaults

		return '{prefix}{colorstart}{msg}{colorend}'.format(
			prefix     = '- ' if first else '  ',
			colorstart = self.theme['optdesc'],
			msg        = msg,
			colorend   = colorama.Style.RESET_ALL
		)

	def assemble(self, helps):
		"""
		Assemble the whole help page.
		@params:
			`helps`: The help items. A list with plain strings or tuples of 3 elements, which
				will be treated as option name, option type/placeholder and option descriptions.
			`progname`: The program name used to replace '{prog}' with.
		@returns:
			lines (`list`) of the help information.
		"""

		ret = []
		maxoptwidth = 0
		for helpitems in helps.values():
			for item in helpitems:
				if not isinstance(item, tuple):
					continue
				# 5 = <first 2 spaces: 2> +
				#     <gap between name and type: 1> +
				#     <brackts around type: 2>
				maxoptwidth = max(maxoptwidth,
					max(len(item[0] + item[1]) + MIN_OPT_GAP + 5
						for item in helpitems
						if len(item[0] + item[1]) + MIN_OPT_GAP + 5 <= MAX_OPT_WIDTH))

		maxoptwidth = maxoptwidth or MAX_OPT_WIDTH

		for title, helpitems in helps.items():

			ret.append(self.title(title))
			if not any(isinstance(item, tuple) for item in helpitems):
				for item in helpitems:
					ret.extend(self.plain(it) for it in _textwrap(
						item, MAX_PAGE_WIDTH - 2, initial_indent = '  ', subsequent_indent = '  '))
				ret.append('')
				continue

			helpitems = [item if isinstance(item, tuple) else ('', '', item)
						 for item in helpitems]

			for optname, opttype, optdesc in helpitems:
				descs = sum((_textwrap(desc, MAX_PAGE_WIDTH - maxoptwidth)
							for desc in optdesc), [])
				optlen = len(optname + opttype) + MIN_OPT_GAP + 5
				if optlen > MAX_OPT_WIDTH:
					ret.append(
						self.optname(optname, prefix = '  ') + ' ' + self.opttype(opttype))
					if descs:
						ret.append(' ' * maxoptwidth + self.optdesc(descs.pop(0), True))
				else:
					to_append = self.optname(optname, prefix = '  ') + ' ' + \
								self.opttype(opttype.ljust(maxoptwidth - len(optname) - 5))
					if descs:
						to_append += self.optdesc(descs.pop(0), True)
					ret.append(to_append)
				if descs:
					ret.extend(' ' * maxoptwidth + self.optdesc(desc) for desc in descs)
			ret.append('')
		ret.append('')
		return ret

class Param(_Valuable):
	"""
	The class for a single parameter
	"""
	def __init__(self, name, value = OPT_UNSET_VALUE):
		"""
		Constructor
		@params:
			`name`:  The name of the parameter
			`value`: The initial value of the parameter
		"""
		self.value, self._type = Param._typeFromValue(value)

		self._desc     = []
		self._required = False
		self.show      = True
		self.name      = name
		self.stacks    = []
		self.callback  = None

		# We cannot change name later on
		if not isinstance(name, str):
			raise ParamNameError(name, 'Not a string')
		if not re.search(r'^[A-Za-z0-9_,\-.]{1,255}$', name):
			raise ParamNameError(name,
				'Expect a string with comma, alphabetics ' +
				'and/or underlines in length 1~255, but we got')

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
			raise ParamTypeError('Subtype %r is only allowed for list and dict' % type2)
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
			return self.value == other.value and (
				not self.type or not other.type or self.type == other.type)
		return self.value == other

	def push(self, value = OPT_UNSET_VALUE, typename = None):
		"""
		Push the value to the stack.
		"""
		# nothing to do, no self.type, no typename and no value
		if typename is None and value == OPT_UNSET_VALUE and self.type == 'auto:':
			return

		# push an item forcely using previous type
		# in case the option is give by '-a 1' without any type specification
		# if no type specified, deduct from the value
		# otherwise auto
		origtype = self.stacks[-1][0] if self.stacks else self.type

		if typename is True:
			typename = origtype
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
					if origtype == 'list:list':
						self.stacks.append((origtype, [[]]))
					else:
						self.stacks.append((origtype, []))
				elif type2 == 'reset':
					self.stacks.append((type1 + ':', []))
				elif type1 == 'list':
					if origtype == typename:
						self.stacks.append((typename, self.value[:]))
					else:
						self.stacks.append((typename, []))
				elif type1 == 'dict':
					if origtype == typename:
						self.stacks.append((typename, [(self.value or {}).copy()]))
					else:
						self.stacks.append((typename, []))
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

			# since container has been created
			self.push(value)
		else:
			if not self.stacks:
				self.push(value, typename = True)
			elif value != OPT_UNSET_VALUE:
				type2 = origtype.split(':')[1]
				prevalue = self.stacks[-1][-1][-1] if type2 == 'list' else self.stacks[-1][-1]
				prevalue.append(value)

	def checkout(self):
		if not self.stacks:
			return []

		typename, value = self.stacks.pop(-1)
		warns = ['Previous settings (type=%r, value=%r) were ignored for option %r' % (
				 wtype, wval, self.name) for wtype, wval in self.stacks]
		self.stacks = []

		type1, type2 = typename.split(':')
		self._type = typename
		if type2 == 'list':
			self.value = value
		elif type1 == 'list':
			self.value = Param._forceType(value, typename)
		elif type1 in ('bool', 'auto') and not value:
			self.value = True
		elif type1 == 'dict':
			if not value:
				self.value = {}
			else:
				val0 = value.pop(0)
				if isinstance(val0, Param):
					val0 = val0.dict()
				for val in value:
					if isinstance(val, Param):
						val = val.dict()
					val0 = Param._dictUpdate(val0, val)
				self.value = val0
		else:
			self.value = Param._forceType(value.pop(0), typename)
			for val in value:
				warns.append('Later value %r was ignored for option %r (type=%r)' % (
					val, self.name, typename))

		return warns

	@property
	def desc(self):
		return self._desc

	@desc.setter
	def desc(self, description):
		assert isinstance(description, (list, str))
		if isinstance(description, str):
			description = description.splitlines()
		if not description:
			description.append('')
		if not self.required and not 'DEFAULT: ' in description[-1] and \
			'Default: ' not in description[-1]:
			if description[-1]:
				description[-1] += ' '
			description[-1] += 'Default: ' + repr(self.value)
		if len(description) == 1 and not description[0]:
			description[0] = '[No description]'
		self._desc = description

	@property
	def required(self):
		return self._required

	@required.setter
	def required(self, req):
		if self.type == 'bool:':
			raise ParamTypeError(
				self.value, 'Bool option %r cannot be set as required' % self.name)
		if self.type == 'NoneType:':
			# make sure required options being detected by validation
			self.type = 'auto:'
		self._required = req

	@property
	def type(self):
		return self._type

	@type.setter
	def type(self, typename):
		self.setType(typename, True)

	@staticmethod
	def _forceType(value, typename):
		if not typename:
			return value
		type1, type2 = typename.split(':')
		try:
			if type1 in ('int', 'float', 'str'):
				return getattr(builtins, type1)(value)

			if type1 == 'bool':
				if value in OPT_BOOL_TRUES:
					return True
				if value in OPT_BOOL_FALSES:
					return False
				raise ParamTypeError('Unable to coerce value %r to bool' % value)

			if type1 == 'NoneType':
				if not value in OPT_NONES:
					raise ParamTypeError('Unexpected value %r for NoneType' % value)
				return None

			if type1 == 'py':
				value = value[3:] if value.startswith('py:') else \
						value[5:] if value.startswith('repr:') else value
				return ast.literal_eval(value)

			if type1 == 'dict':
				if not isinstance(value, dict):
					if not value:
						value = {}
					try:
						value = dict(value)
					except TypeError:
						raise ParamTypeError('Cannot coerce %r to dict.' % value)
				return OrderedDict(value.items())

			if type1 == 'auto':
				try:
					if re.match(OPT_NONE_PATTERN, value):
						typename = 'NoneType'
					elif re.match(OPT_INT_PATTERN, value):
						typename = 'int'
					elif re.match(OPT_FLOAT_PATTERN, value):
						typename = 'float'
					elif re.match(OPT_BOOL_PATTERN, value):
						typename = 'bool'
					elif re.match(OPT_PY_PATTERN, value):
						typename = 'py'
					else:
						typename = 'str'
					return Param._forceType(value, Param._normalizeType(typename))
				except TypeError: # value is not a string, cannot do re.match
					return value

			if type1 == 'list':
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
					return value if value and isinstance(value[0], list) else [value]
				type2 = Param._normalizeType(type2)
				return [Param._forceType(x, type2) for x in value]

			raise TypeError
		except (ValueError, TypeError):
			raise ParamTypeError('Unable to coerce value %r to type %r' % (value, typename))

	def dict(self):
		if '.' not in self.name:
			raise ParamTypeError(
				'Unable to convert param into dict without dot in name: %r' % self.name)
		ret0 = ret = {}
		parts = self.name.split('.')
		for part in parts[1:-1]:
			ret[part] = {}
			ret = ret[part]
		ret[parts[-1]] = self.value
		return ret0

	def __repr__(self):
		typename = self.type or ''
		return '<Param(name={!r},value={!r},type={!r}) @ {}>'.format(
			self.name, self.value, typename.rstrip(':'), hex(id(self)))

	def setDesc (self, desc):
		"""
		Set the description of the parameter
		@params:
			`desc`: The description
		"""
		self.desc = desc
		return self

	def setRequired (self, req = True):
		"""
		Set whether this parameter is required
		@params:
			`req`: True if required else False. Default: True
		"""
		self.required = req
		return self

	def setType (self, typename, update_value = True):
		"""
		Set the type of the parameter
		@params:
			`typename`: The type of the value. Default: str
			- Note: str rather then 'str'
		"""
		if not isinstance(typename, str):
			typename = typename.__name__
		self._type = Param._normalizeType(typename)
		if update_value:
			self.value = Param._forceType(self.value, self._type)
		return self

	def setCallback(self, callback):
		"""
		Set callback
		@params:
			`callback`: The callback
		"""
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

	def setValue(self, value, update_type = False):
		"""
		Set the value of the parameter
		@params:
			`val`: The value
		"""
		if update_type:
			self.value, self._type = Param._typeFromValue(value)
		else:
			self.value = value
		return self

class Params(_Hashable):
	"""
	A set of parameters
	"""

	def __init__(self, command = None, theme = 'default'):
		"""
		Constructor
		@params:
			`command`: The sub-command
			`theme`: The theme
		"""
		prog = path.basename(sys.argv[0])
		prog = prog + ' ' + command if command else prog
		self.__dict__['_props'] = dict(
			prog      = prog,
			usage     = [],
			desc      = [],
			hopts     = ['-h', '--help', '-H'],
			prefix    = '-',
			hbald     = True,
			assembler = HelpAssembler(prog, theme),
			helpx     = None
		)
		self.__dict__['_params']    = OrderedDict()

	def __setattr__(self, name, value):
		"""
		Change the value of an existing `Param` or create a `Param`
		using the `name` and `value`. If `name` is an attribute, return its value.
		@params:
			`name` : The name of the Param
			`value`: The value of the Param
		"""
		if name.startswith('__') or name.startswith('_' + self.__class__.__name__):
			super(Params, self).__setattr__(name, value)
		elif isinstance(value, Param):
			self._params[name] = value
		elif name in self._params:
			self._params[name].value = value
		elif name in ('_assembler', '_helpx', '_prog'):
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
		if name.startswith('__') or name.startswith('_' + self.__class__.__name__):
			return super(Params, self).__getattr__(name)
		if name in ['_' + key for key in self._props.keys()]:
			return self._props[name[1:]]
		if not name in self._params:
			self._params[name] = Param(name, None)
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
		self._props['usage'] = usage if isinstance(usage, list) else usage.splitlines()
		return self

	def _setDesc(self, desc):
		"""
		Set the description
		@params:
			`desc`: The description
		"""
		assert isinstance(desc, (list, str))
		self._props['desc'] = desc if isinstance(desc, list) else desc.splitlines()
		return self

	def _setHopts(self, hopts):
		"""
		Set the help options
		@params:
			`hopts`: The help options
		"""
		assert isinstance(hopts, (list, str))
		self._props['hopts'] = hopts if isinstance(hopts, list) else \
			[ho.strip() for ho in hopts.split(',')]
		return self

	def _setPrefix(self, prefix):
		"""
		Set the option prefix
		@params:
			`prefix`: The prefix
		"""
		if not prefix:
			raise ParamsParseError('Empty prefix.')
		self._props['prefix'] = prefix
		return self

	def _setHbald(self, hbald = True):
		"""
		Set if we should show help information if no arguments passed.
		@params:
			`hbald`: The flag. show if True else hide. Default: `True`
		"""
		self._props['hbald'] = hbald
		return self

	def __repr__(self):
		return '<Params({}) @ {}>'.format(','.join(
			'{p.name}:{p.type}'.format(p = param) for param in self._params.values()
		), hex(id(self)))

	def _preParse(self, args):
		"""
		Parse the arguments from command line
		Don't coerce the types and values yet.
		"""
		parsed   = OrderedDict()
		pendings = []
		lastopt  = None
		for arg in args:
			if arg.startswith(self._prefix):
				argtoparse = arg[len(self._prefix):]
				matches = re.match(OPT_PATTERN, argtoparse)
				# if it is not an option, treat it as value
				# for example, negative numbers: -1, -2
				if not matches:
					if lastopt is None:
						pendings.append(arg)
					else:
						lastopt.push(arg)
					continue

				argname = matches.group(1) or OPT_POSITIONAL_NAME
				argtype = matches.group(2)
				argval  = matches.group(3) or OPT_UNSET_VALUE

				if argname in parsed:
					lastopt = parsed[argname]
				else:
					lastopt = self._params[argname] \
						if argname in self._params else Param(argname, []) \
						if argname == OPT_POSITIONAL_NAME and not argtype else Param(argname)
					parsed[argname] = lastopt

				lastopt = parsed[argname]
				lastopt.push(argval, argtype or True)

				if '.' in argname:
					doptname = argname.split('.')[0]
					if doptname in parsed:
						dictopt = parsed[doptname]
					else:
						dictopt = self._params[doptname] \
							if doptname in self._params else Param(doptname, {})
						parsed[doptname] = dictopt
					dictopt.push(lastopt, 'dict:')

			elif lastopt is None:
				pendings.append(arg)
			else:
				lastopt.push(arg)

		# no options detected at all
		# all pendings will be used as positional
		if lastopt is None and pendings:
			parsed[OPT_POSITIONAL_NAME] = Param(OPT_POSITIONAL_NAME, [])
			for pend in pendings:
				parsed[OPT_POSITIONAL_NAME].push(pend)
			pendings = []
		elif lastopt is not None:
			# lastopt is not list, so use the values pushed as positional
			posvalues = []
			if not lastopt.stacks or lastopt.stacks[-1][0].startswith('list:') or \
				len(lastopt.stacks[-1][1]) < 2:
				posvalues = []
			else:
				posvalues = lastopt.stacks[-1][1][1:]
				lastopt.stacks[-1] = (lastopt.stacks[-1][0], lastopt.stacks[-1][1][:1])

			# is it necessary to create positional?
			# or it is already there
			# if it is already there, that means tailing values should not be added to positional
			if OPT_POSITIONAL_NAME in parsed or not posvalues:
				pendings.extend(posvalues)
				return parsed, pendings

			posopt = Param(OPT_POSITIONAL_NAME, [])
			parsed[OPT_POSITIONAL_NAME] = posopt
			for posval in posvalues:
				posopt.push(posval)

		return parsed, pendings

	def parse(self, args = None, arbi = False, dict_wrapper = dict, raise_exc = False):
		args = sys.argv[1:] if args is None else args
		try:
			if not args and self._hbald:
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
				if name in self._params:
					pass
				elif arbi:
					self._params[name] = param
				elif self._prefix + name in self._hopts:
					raise ParamsParseError('__help__')
				else:
					warns.append('Unrecognized option: %r' % (self._prefix + name))
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
				raise ParamsParseError('Option %r: %s' % (self._prefix + name, error))

			# check required
			for name, param in self._params.items():
				if param.required and param.value is None and param.type != 'NoneType:':
					raise ParamsParseError('Option %r is required.' % (self._prefix + name))

			for warn in warns[:(MAX_WARNINGS+1)]:
				sys.stderr.write(warn + '\n')
			return self.asDict(dict_wrapper)
		except ParamsParseError as exc:
			if raise_exc:
				raise
			exc = str(exc)
			if exc == '__help__':
				exc = ''
			self.help(exc, print_and_exit = True)

	def _helpitems(self):
		# alias
		revparams = {}
		for key, val in self._params.items():
			if not val in revparams:
				revparams[val] = []
			revparams[val].append(key)

		posopt = None
		if OPT_POSITIONAL_NAME in self._params:
			posopt = self._params[OPT_POSITIONAL_NAME]

		required_options   = []
		optional_options   = []

		for val in revparams.keys():
			# options not suppose to show
			if not val.show or val.name == OPT_POSITIONAL_NAME:
				continue

			# Force calculate default in description
			val.desc = val.desc
			valtype  = val.type or ''
			valtype  = valtype.rstrip(':')
			if valtype == 'NoneType':
				valtype = 'auto'
			option = (
				', '.join([self._props['prefix'] + k
						   for k in sorted(revparams[val], key = len)]),
				valtype, val.desc)
			if val.required:
				required_options.append(option)
			else:
				optional_options.append(option)

		if isinstance(posopt, Param):
			# force description generation
			posopt.desc = posopt.desc
			if posopt.required:
				required_options.append(('POSITIONAL', '', posopt.desc))
			else:
				optional_options.append(('POSITIONAL', '', posopt.desc))

		helpitems = OrderedDict()
		if self._props['desc']:
			helpitems['description'] = self._props['desc']

		if self._props['usage']:
			helpitems['usage'] = sum((_textwrap(
				usage, MAX_PAGE_WIDTH - (len(self._prog) - 6) * 4 - 10, subsequent_indent = '  ')
				for usage in self._props['usage']), [])
		else: # default usage
			defusage = ['{prog}']
			for optname, opttype, _ in required_options:
				if optname == 'POSITIONAL':
					continue
				defusage.append('<{} {}>'.format(
					optname.split(',')[0],
					opttype or optname[len(self._props['prefix']):].upper())
				)
			if optional_options:
				defusage.append('[OPTIONS]')
			if isinstance(posopt, Param):
				defusage.append('POSITIONAL' if posopt.required else '[POSITIONAL]')

			if len(defusage) == 1:
				defusage.append('[OPTIONS]')

			defusage = _textwrap(' '.join(defusage),
				MAX_PAGE_WIDTH - (len(self._prog) - 6) * 4 - 10, subsequent_indent = '  ')
			helpitems['usage'] = defusage

		optional_options.append((
			', '.join(filter(None, self._props['hopts'])),
			'', ['Print this help information']))
		if required_options:
			helpitems[REQUIRED_OPT_TITLE] = required_options
		if optional_options:
			helpitems[OPTIONAL_OPT_TITLE] = optional_options

		if callable(self._helpx):
			helpitems = self._helpx(helpitems)

		return helpitems

	def help (self, error = '', print_and_exit = False):
		"""
		Calculate the help page
		@params:
			`error`: The error message to show before the help information. Default: `''`
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
		ret.extend(self._assembler.assemble(self._helpitems()))

		if print_and_exit:
			sys.stderr.write('\n'.join(ret))
			sys.exit(1)
		else:
			return '\n'.join(ret)

	def loadDict (self, dict_var, show = False):
		"""
		Load parameters from a dict
		@params:
			`dict_var`: The dict variable.
			- Properties are set by "<param>.required", "<param>.show", ...
			`show`:    Whether these parameters should be shown in help information
				- Default: False (don'typename show parameter from config object in help page)
				- It'll be overwritten by the `show` property inside dict variable.
				- If it is None, will inherit the param's show value
		"""
		# load the param first
		for key, val in dict_var.items():
			if '.' in key:
				continue
			if not key in self._params:
				self._params[key] = Param(key, val)
			self._params[key].value = val
			if show is not None:
				self._params[key].show = show
		# then load property
		for key, val in dict_var.items():
			if '.' not in key:
				continue
			opt, prop = key.split('.', 1)
			if not opt in self._params:
				raise ParamsLoadError('Cannot set attribute of an undefined option %r' % opt)
			if not prop in ['desc', 'required', 'show', 'type']:
				raise ParamsLoadError('Unknown attribute %r for option %r' % (prop, opt))

			setattr(self._params[opt], prop, val)
		return self

	def loadFile (self, cfgfile, profile = False, show = False):
		"""
		Load parameters from a json/config file
		If the file name ends with '.json', `json.load` will be used,
		otherwise, `ConfigParser` will be used.
		For config file other than json, a section name is needed, whatever it is.
		@params:
			`cfgfile`: The config file
			`show`:    Whether these parameters should be shown in help information
				- Default: False (don'typename show parameter from config file in help page)
				- It'll be overwritten by the `show` property inside the config file.
		"""
		config = Config(with_profile = bool(profile))
		config._load(cfgfile)
		if profile:
			config._use(profile)
		return self.loadDict(config, show = show)

	def asDict (self, wrapper = dict):
		"""
		Convert the parameters to dict object
		@returns:
			The dict object
		"""
		ret = wrapper()
		for name in self._params:
			ret[name] = self._params[name].value
		return ret

	dict = asDict
	load = loadDict

class Commands(object):
	"""
	Support sub-command for command line argument parse.
	"""

	def __init__(self, theme = 'default', prefix = '-'):
		"""
		Constructor
		@params:
			`theme`: The theme
		"""
		self.__dict__['_props'] = dict(
			_desc     = [],
			_hcmd     = ['help'],
			cmds      = OrderedDict(),
			assembler = HelpAssembler(None, theme),
			helpx     = None,
			prefix    = prefix
		)
		self._cmds[CMD_COMMON_PARAMS] = Params(None, theme)
		self._cmds[CMD_COMMON_PARAMS]._prefix = prefix
		self._cmds[CMD_COMMON_PARAMS]._hbald  = False

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
		self._hcmd = hcmd
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
		if name.startswith('__') or name.startswith('_' + self.__class__.__name__):
			return super(Commands, self).__getattr__(name)
		if name in ('_desc', '_hcmd'):
			return self._props[name]
		if name in ('_cmds', '_assembler', '_helpx', '_prefix'):
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
		if name.startswith('__') or name.startswith('_' + self.__class__.__name__):
			super(Commands, self).__setattr__(name, value)
		elif name == '_theme':
			self._assembler = HelpAssembler(None, value)
		elif name == '_hcmd':
			self._props['_hcmd'] = [cmd.strip() for cmd in value.split(',')] \
				if isinstance(value, str) else value
		elif name == '_desc':
			self._props['_desc'] = value.splitlines() if isinstance(value, str) else value
		elif name == '_prefix':
			self._props['prefix'] = value
			for cmd in self._cmds.values():
				cmd._prefix = value
		elif name in ('_cmds', '_assembler', '_helpx'):
			self._props[name[1:]] = value
		elif isinstance(value, Params): # alias
			self._cmds[name] = value
			if name != value._prog.split()[-1]:
				value._prog += '|' + name
				value._assembler = HelpAssembler(value._prog, value._assembler.theme)
		else:
			if name not in self._cmds:
				self._cmds[name] = Params(name, self._assembler.theme)
				self._cmds[name]._prefix = self._prefix
			self._cmds[name]._desc = value

	__getitem__ = __getattr__
	__setitem__ = __setattr__

	def parse(self, args = None, arbi = False, dict_wrapper = dict):
		"""
		Parse the arguments.
		@params:
			`args`: The arguments (list). `sys.argv[1:]` will be used if it is `None`.
			`arbi`: Whether do an arbitrary parse.
				If True, options do not need to be defined. Default: `False`
		@returns:
			A `tuple` with first element the subcommand and second the parameters being parsed.
		"""
		args = sys.argv[1:] if args is None else args
		# the commands have to be defined even for arbitrary mode
		try:
			if not args:
				raise CommandsParseError('__help__')
			# get which command is hit
			cmdidx  = None
			command = None
			for i, arg in enumerate(args):
				if arg == 'help':
					raise CommandsParseError('__help__')

				if arg != CMD_COMMON_PARAMS and arg in self._cmds:
					command = arg
					cmdidx = i
					break
			else:
				raise CommandsParseError('No command given.')

			common_args = args[:cmdidx]
			try:
				common_opts = self._cmds[CMD_COMMON_PARAMS].parse(
					common_args, arbi, dict_wrapper, True)
			except ParamsParseError as exc:
				raise CommandsParseError(str(exc))

			command_args = args[(cmdidx+1):]
			command_opts = self._cmds[command].parse(
				command_args, arbi, dict_wrapper)

			return command, command_opts, common_opts

		except CommandsParseError as exc:
			exc = str(exc)
			if exc == '__help__':
				exc = ''
			self.help(error = exc, print_and_exit = True)

	def help(self, error = '', print_and_exit = False):
		"""
		Construct the help page
		@params:
			`error`: the error message
			`print_and_exit`: print the help page and exit instead of return the help information
		@returns:
			The help information if `print_and_exit` is `False`
		"""
		helpitems = OrderedDict()
		if self._desc:
			helpitems['description'] = self._desc

		helpitems['usage'] = ['{prog} [COMMON OPTIONS] <command> [COMMAND OPTIONS]']

		common_opt_items = self._cmds[CMD_COMMON_PARAMS]._helpitems()
		if REQUIRED_OPT_TITLE in common_opt_items:
			helpitems[REQUIRED_OPT_TITLE] = common_opt_items[REQUIRED_OPT_TITLE]
		if OPTIONAL_OPT_TITLE in common_opt_items:
			helpitems[OPTIONAL_OPT_TITLE] = common_opt_items[OPTIONAL_OPT_TITLE]

		helpitems['commands'] = []
		revcmds = OrderedDict()
		for key, val in self._cmds.items():
			if key == CMD_COMMON_PARAMS:
				continue
			if val not in revcmds:
				revcmds[val] = []
			revcmds[val].append(key)

		for key, val in revcmds.items():
			helpitems['commands'].append((' | '.join(val), '', key._desc))
		helpitems['commands'].append(
			(' | '.join(self._hcmd), 'command', ['Print help information for the command']))

		if callable(self._helpx):
			helpitems = self._helpx(helpitems)

		ret = []
		if error:
			if isinstance(error, str):
				error = error.splitlines()
			ret = [self._assembler.error(err.strip()) for err in error]
		ret.extend(self._assembler.assemble(helpitems))

		if print_and_exit:
			sys.stderr.write('\n'.join(ret))
			sys.exit(1)
		else:
			return '\n'.join(ret)

# pylint: disable=invalid-name
params   = Params()
commands = Commands()
