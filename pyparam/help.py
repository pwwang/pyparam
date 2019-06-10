"""Help stuff for help message"""
import re
from collections import OrderedDict

def _match(selector, item, regex = False):
	isinstance(selector, (str, re.Pattern))
	if isinstance(selector, str) and regex:
		selector = re.compile(selector)

	if isinstance(selector, re.Pattern):
		return bool(selector.search(item[0] if isinstance(item, tuple) else item))

	if isinstance(item, tuple):
		items = item[0].split(', ')
		return selector in items or selector in (it.lstrip('-') for it in items)
	return selector in item

class HelpItems(list):
	"""
	An item of a help message without divisions.
	For example, a line of description, usage or example.
	"""
	def __init__(self, *args, **kwargs):
		for arg in args:
			self.add(arg)

	def add(self, item):
		if not isinstance(item, list):
			item = item.splitlines()
		self.extend(item)

	def query(self, selector, regex = False):
		for i, item in enumerate(self):
			if _match(selector, item, regex):
				return i
		raise ValueError('No element found by selector: %r' % selector)

	def after(self, selector, item, **kwargs):
		index = self.query(selector, kwargs.pop('regex', False)) + 1
		if not isinstance(item, list):
			item = item.splitlines()
		self[index:index] = item

	def before(self, selector, item, **kwargs):
		index = self.query(selector, kwargs.pop('regex', False))
		if not isinstance(item, list):
			item = item.splitlines()
		self[index:index] = item

	def replace(self, selector, content, **kwargs):
		index = self.query(selector, kwargs.pop('regex', False))
		self[index] = content

	def select(self, selector, **kwargs):
		return self[self.query(selector, kwargs.pop('regex', False))]

	def delete(self, selector, **kwargs):
		del self[self.query(selector, kwargs.pop('regex', False))]

class HelpOptionDescriptions(HelpItems):
	"""Option description in help page"""

class HelpOptions(HelpItems):
	"""All options of an option section"""

	def __init__(self, *args, **kwargs):
		self.prefix = kwargs.pop('prefix', 'auto')
		super(HelpOptions, self).__init__(*args, **kwargs)

	def _prefixName(self, name):
		if name.startswith('-') or not self.prefix:
			return name
		if self.prefix != 'auto':
			return self.prefix + name
		return '-' + name if len(name) <= 1 or name[1] == '.' else '--' + name

	def addParam(self, param, aliases = None, ishelp = False):
		aliases = set(aliases) or set()
		aliases.add(param.name)
		if param.type == 'verbose:':
			aliases.add('-' + param.name * 2)
			aliases.add('-' + param.name * 3)
		paramtype = '<VERBOSITY>' if param.type == 'verbose:' else '' \
			if ishelp else '[BOOL]' \
			if param.type == 'bool:' else '<%s>' % param.type.rstrip(':').upper()
		self.add((
			', '.join(self._prefixName(alias) for alias in sorted(aliases, key = len)),
			paramtype,
			param.desc
		))

	def addCommand(self, params, aliases, ishelp = False):
		cmdtype = '[COMMAND]' if ishelp else ''
		self.add((
			', '.join(sorted(set(aliases), key = len)),
			cmdtype,
			params._desc
		))

	def add(self, item, aliases = None, ishelp = False):
		from . import Param, Params
		if isinstance(item, Param):
			self.addParam(item, aliases, ishelp)
		elif isinstance(item, Params):
			self.addCommand(item, aliases, ishelp)
		elif not isinstance(item, tuple) or len(item) != 3:
			raise ValueError('Expect a 3-element tuple as an option item in help page.')
		elif not isinstance(item[2], HelpItems):
			item = item[:2] + (HelpOptionDescriptions(item[2]),)
			self.append(item)
		else:
			self.append(item)

class Helps(OrderedDict):
	"""All sections of help"""

	def _insertAfter(self, key, section, item):
		link = self.__map[key]
		self.__map[section] = [link, link.next, section]
		link.next = link.next.prev = self.__map[section]
		dict.__setitem__(self, section, item)

	def _insertBefore(self, key, section, item):
		link = self.__map[key]
		self.__map[section] = [link.prev, link, section]
		link.prev = link.prev.next = self.__map[section]
		dict.__setitem__(self, section, item)

	def query(self, selector, regex = False):
		for key in self:
			if _match(selector, key, regex):
				return key
		raise ValueError('No section found by selector: %r' % selector)

	def select(self, selector, regex = False):
		return self[self.query(selector, kwargs.pop('regex', False))]

	@staticmethod
	def _section(*args, **kwargs):
		if len(args) == 1 and isinstance(args[0], HelpOptions):
			return args[0]
		if len(args) == 1 and isinstance(args[0], HelpItems):
			return args[0]
		try:
			return HelpOptions(*args, **kwargs)
		except ValueError:
			return HelpItems(*args, **kwargs)

	def add(self, section, *args, **kwargs):
		self[section] = Helps._section(*args, **kwargs)

	def before(self, selector, section, *args, **kwargs):
		key = self.query(selector, kwargs.pop('regex', False))
		self._insertBefore(key, section, Helps._section(*args, **kwargs))

	def after(self, selector, section, *args, **kwargs):
		key = self.query(selector, kwargs.pop('regex', False))
		self._insertAfter(key, section, Helps._section(*args, **kwargs))
