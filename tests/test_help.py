import re
import pytest
from pyparam.help import _match, HelpItems, HelpOptions, HelpOptionDescriptions, Helps
from pyparam import Param, Params

@pytest.mark.parametrize('selector, item, regex, expt', [
	(r'what\d+ever', '1what123ever', True, True),
	(re.compile(r'what\d+ever'), '1what123ever', True, True),
	(r'what\d+ever', '1whxat123ever', True, False),
	(re.compile(r'what\d+ever'), '1whxat123ever', True, False),
	('what', 'what123ever', False, True),
	('what', 'whxat123ever', False, False),
	(r'-o, --o', ('-o, --output',), True, True),
	(re.compile(r'-o, --o'), ('-o, --output',), True, True),
	(r'-o,\d--o', ('-o, --output',), True, False),
	(re.compile(r'-o,\d--o'), ('-o, --output',), True, False),
	('-o', ('-o, --output',), False, True),
	('output', ('-o, --output',), False, True),
	('-ou', ('-o, --output',), False, False),
])
def test_match(selector, item, regex, expt):
	assert _match(selector, item, regex) is expt

def test_helpitems():

	hi = HelpItems()
	assert hi == []

	hi = HelpItems(["a", "b"])
	assert hi == ["a", "b"]

	hi = HelpItems("a", "b")
	assert hi == ["a", "b"]

	hi = HelpItems("a\nb")
	assert hi == ["a", "b"]

	hi = HelpItems()
	hi.add(["a", "b"])
	assert hi == ["a", "b"]

	hi = HelpItems()
	hi.add("a")
	hi.add("b")
	assert hi == ["a", "b"]

	hi = HelpItems()
	hi.add("a\nb")
	assert hi == ["a", "b"]

@pytest.mark.parametrize("items,selector,regex,expt", [
	(["abc", "a1bc"], "bc", False, 0),
	(["abc", "a1bc"], "1bc", False, 1),
	(["abc", "a1bc"], "1bc", False, 1),
	(["abc", "a1bc"], r"\dbc", True, 1),
])
def test_helpitems_query(items, selector, regex, expt):
	assert HelpItems(items).query(selector, regex) == expt

def test_helpitems_query_exc():
	with pytest.raises(ValueError):
		HelpItems([]).query('')

def test_helpitems_operations():
	hi = HelpItems("abc\ndef\nhij")
	hi.before("def", "ccc")
	assert hi == ["abc", "ccc", "def", "hij"]
	hi.after("cc", "999")
	assert hi == ["abc", "ccc", "999", "def", "hij"]
	hi.replace("cc", "xxxx")
	assert hi == ["abc", "xxxx", "999", "def", "hij"]
	assert hi.select('9') == '999'
	hi.delete('9')
	assert hi == ["abc", "xxxx", "def", "hij"]

def test_helpoptions():
	ho = HelpOptions()
	assert ho == []
	assert ho.prefix == 'auto'

	ho = HelpOptions(('', '', 'a'), ('', '', 'b'), prefix = '-')
	assert ho == [('', '', ['a']), ('', '', ['b'])]
	assert ho.prefix == '-'

@pytest.mark.parametrize("name, prefix,expt", [
	('-a', '', '-a'),
	('a', '', 'a'),
	('a', '-', '-a'),
	('a', 'auto', '-a'),
	('a.b', 'auto', '-a.b'),
	('ab', 'auto', '--ab'),
])
def test_helpoptions_prefixname(name, prefix, expt):
	assert HelpOptions(prefix = prefix)._prefixName(name) == expt

@pytest.mark.parametrize("param, aliases, ishelp, prefix, expt", [
	(Param('v', 0).setType('verbose'),
	 ['verbose'], False, 'auto',
	 [('-v, -vv, -vvv, --verbose', '<VERBOSITY>', ['Default: 0'])]),
	(Param('a', False),
	 ['auto'], False, 'auto',
	 [('-a, --auto', '[BOOL]', ['Default: False'])]),
	(Param('d', 1).setDesc('Whehter to show the description or not.'),
	 ['desc'], False, 'auto',
	 [('-d, --desc', '<INT>', ['Whehter to show the description or not.', 'Default: 1'])]),
])
def test_helpoptions_addparam(param, aliases, ishelp, prefix, expt):
	ho = HelpOptions(prefix = prefix)
	ho.addParam(param, aliases, ishelp)
	assert ho == expt

@pytest.mark.parametrize("params, aliases, ishelp, expt", [
	(Params()._setDesc('Command 1'),
	 ['cmd1'], False,
	 [('cmd1', '', ['Command 1'])]),
	(Params()._setDesc('Print help page and exit'),
	 ['help'], True,
	 [('help', '[COMMAND]', ['Print help page and exit'])]),
])
def test_helpoptions_addcommand(params, aliases, ishelp, expt):
	ho = HelpOptions()
	ho.addCommand(params, aliases, ishelp)
	assert ho == expt

@pytest.mark.parametrize("param, aliases, ishelp, prefix, expt", [
	(Param('v', 0).setType('verbose'),
	 ['verbose'], False, 'auto',
	 [('-v, -vv, -vvv, --verbose', '<VERBOSITY>', ['Default: 0'])]),
	(Param('a', False),
	 ['auto'], False, 'auto',
	 [('-a, --auto', '[BOOL]', ['Default: False'])]),
	(Param('d', 1).setDesc('Whehter to show the description or not.'),
	 ['desc'], False, 'auto',
	 [('-d, --desc', '<INT>', ['Whehter to show the description or not.', 'Default: 1'])]),
	 (Params()._setDesc('Command 1'),
	 ['cmd1'], False, 'auto',
	 [('cmd1', '', ['Command 1'])]),
	(Params()._setDesc('Print help page and exit'),
	 ['help'], True, 'auto',
	 [('help', '[COMMAND]', ['Print help page and exit'])]),
	(('-option', '<INT>', HelpOptionDescriptions("Description 1", "Description 2")),
	 [], False, 'auto',
	 [('-option', '<INT>', ["Description 1", "Description 2"])])
])
def test_helpoptions_add(param, aliases, ishelp, prefix, expt):
	ho = HelpOptions(prefix = prefix)
	ho.add(param, aliases, ishelp)
	assert ho == expt

def test_helpoptions_add_exc():
	ho = HelpOptions()
	with pytest.raises(ValueError):
		ho.add((1,))
