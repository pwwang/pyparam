# pyparam
[![pypi][1]][2] [![travis][3]][4] [![codacy quality][5]][6] [![codacy quality][7]][6] ![pyver][8]

Powerful parameter processing

## Installation
`pip install pyparam`

## Usage
### Parameters from command line arguments
- Basic usage

	`program.py`
	```python
	from pyparam import params
	# define arguments
	params.opt1 = '1' # default value
	params.opt1.desc = 'This is option 1'
	# required option
	params.opt2.required = True
	params.opt2.desc = 'This is option 2'
	# Alias
	params.o = params.opt2
	# define type of an option
	params.opt3.required = True
	params.opt3.type = int # or 'int'
	params.opt3.desc = 'This is option 3'

	print(params._parse())
	```
	```shell
	> python program.py
	```
	![help][9]

	```shell
	> python program.py --opt2 1 --opt3 4 --opt1 5
	{'h': False, 'help': False, 'H': False, 'opt1': '5', 'opt2': 1, 'o': 1, 'opt3': 4}

	> python program.py -o --opt3 4 --opt1 5
	{'h': False, 'help': False, 'H': False, 'opt1': '5', 'opt2': True, 'o': True, 'opt3': 4}

	> python program.py --opt2 1 --opt3 x --opt1 5
	Traceback (most recent call last):
	... ...
		raise ParamTypeError('Unable to coerce value %r to type %r' % (value, typename))
	param.ParamTypeError: Unable to coerce value 'x' to type 'int:'
	```

	- Fixed prefix
	```python
	params._prefix = '-'
	```
	```shell
	> python program.py -opt2 1 -opt3 4 -opt1 5
	{'h': False, 'help': False, 'H': False, 'opt1': '5', 'opt2': 1, 'o': 1, 'opt3': 4}
	```

- Callbacks
	```python
	from os import path
	from pyparam import params
	params._prefix = '-'
	params.o.required = True
	params.o.callback = lambda param: 'Directory of output file does not exist.' \
		if not path.exists(path.dirname(param.value)) else None
	print(params._parse())
	```
	```shell
	python program.py -o /path/not/exists/outfile
	```
	![callback_error][11]

	Modify value with other options:
	```python
	params.amplifier = 10
	params.number.type = int
	params.number.callback = lambda param, ps: param.setValue(param.value * ps.amplifier.value)
	```
	```shell
	> python program.py -amplifier 100 -number 2
	{'h': False, 'help': False, 'H': False, 'amplifier': 100, 'number': 200}
	```

- Type redefinition
	```python
	# option 'opt' defined but no value and no type defined ('auto' implied)
	param.opt.desc = 'Option'
	```
	```shell
	> python program.py --opt 1
	{'h': False, 'help': False, 'H': False, 'opt': 1}

	> python program.py --opt a
	{'h': False, 'help': False, 'H': False, 'opt': 'a'}

	# force str
	> python program.py --opt:str 1
	{'h': False, 'help': False, 'H': False, 'opt': '1'}
	```

- List/Array options
	```python
	params.infiles.type = list
	```
	```shell
	> python program.py -infiles file1 file2 file3 # or
	> python program.py -infiles file1 -infiles file2 -infiles file3
	{'h': False, 'help': False, 'H': False, 'infiles': ['file1', 'file2', 'file3']}
	```

	Default values:
	```python
	params.infiles = ['file0']
	```
	```shell
	> python program.py -infiles file1 file2 file3
	{'h': False, 'help': False, 'H': False, 'infiles': ['file0', 'file1', 'file2', 'file3']}
	```

	Reset list options
	```shell
	> python program.py -infiles:reset file1 -infiles file2 -infiles file3 # or
	> python program.py -infiles:reset file1 file2 file3 # or
	> python program.py -infiles:list:reset file1 file2 file3
	# or use short names `l:r` for `list:reset`
	{'h': False, 'help': False, 'H': False, 'infiles': ['file1', 'file2', 'file3']}
	```

	Elements are convert using `auto` type:
	```shell
	> python program.py -infiles file1 file2 3
	{'h': False, 'help': False, 'H': False, 'infiles': ['file0', 'file1', 'file2', 3]}
	# to force all str type, note the option is reset
	> python program.py -infiles:list:str file1 file2 3
	{'h': False, 'help': False, 'H': False, 'infiles': ['file1', 'file2', '3']}
	```

	List of list options
	```python
	params.files = ['file01', 'file02']
	params.files.type = 'list:list'
	```
	```shell
	> python program.py -files file11 file12 -files 3
	{'h': False, 'help': False, 'H': False,
	 'infiles': [['file01', 'file02'], ['file11', 'file12'], ['3']]}
	# Note that list:list don't to auto conversion for elements
	# reset list:list
	> python program.py -files:r file11 file12 -files 3
	{'h': False, 'help': False, 'H': False, 'infiles': [['file11', 'file12'], ['3']]}
	```

- Positional options
	```python
	params._.desc = 'Positional option'
	```
	```shell
	> python program.py file1
	{'h': False, 'help': False, 'H': False, '_': ['file1']}
	```

	If last option is a list option:
	```python
	params.infiles = []
	params._.desc = 'Positional option'
	```
	```shell
	> python program.py -infiles file1 file2 file3
	{'h': False, 'help': False, 'H': False, 'infiles': ['file1', 'file2', 'file3'], '_': None}
	# If I want file3 to be the positional option
	> python program.py -infiles file1 file2 - file3
	{'h': False, 'help': False, 'H': False, 'infiles': ['file1', 'file2'], '_': 'file3'}
	```

- Dict options
	```python
	params.config = {'default': 1}
	```
	```shell
	> python program.py -config.width 10 -config.height 20 -config.sub.switch
	{'h': False, 'help': False, 'H': False,
	 'config': {'default': 1, 'width': 10, 'height': 20, 'sub': {'switch': True}}}
	# reset dict option
	> python program.py -config:r -config.width 10 -config.height 20
	{'h': False, 'help': False, 'H': False, 'config': {'width': 10, 'height': 20}}
	```

- Arbitrary parsing
	Parse the arguments without definition
	```python
	print(params._parse(arbi = True))
	```
	```shell
	> python program.py -a 1 -b:list 2 3 -c:dict -c.a.b 4 -c.a.c 5 -d:list:list 6 7 -d 8 9
	{'h': False, 'help': False, 'H': False,
	 'a': 1, 'b': [2, 3], 'c': {'a': {'b': 4, 'c': 5}}, 'd': [['6', '7'], ['8', '9']]}
	```

### Help message
- Themes
	```python
	from pyparam import params
	params._theme = 'blue'
	print(params._parse())
	```
	```shell
	> python program.py
	```
	![theme_blue][13]
	```python
	params._theme = 'plain'
	```
	![theme_blue][14]

	Customize theme based on default theme:
	```python
	dict(
		error   = colorama.Fore.RED,
		warning = colorama.Fore.YELLOW,
		title   = colorama.Style.BRIGHT + colorama.Fore.CYAN,  # section title
		prog    = colorama.Style.BRIGHT + colorama.Fore.GREEN, # program name
		default = colorama.Fore.MAGENTA,              # default values
		optname = colorama.Style.BRIGHT + colorama.Fore.GREEN,
		opttype = colorama.Fore.BLUE,
		optdesc = ''),
	```
	```python
	import colorama
	from pyparam import params
	params._theme = dict(title = colorama.Style.BRIGHT + colorama.Fore.YELLOW)
	print(params._parse())
	```
	![theme_custom][15]

- Manipulation of the message
	Help message is first transformed into a `list`, where the element is a `tuple` of (option name, type and description) if it is an option otherwise a string, and then formatted with the `HelpAssembler` class.
	A callback is available to operate on the transformed message so that the help page can be hacked.
	```python
	from pyparam import params
	params.a = 1
	print(params._helpitems())
	# OrderedDict([
	#   ('usage', ['{prog} [OPTIONS]']),
	#   ('OPTIONAL OPTIONS', [
	#       ('-a', 'int', ['Default: 1']),
	#       ('-h, --help, -H', '', ['Print this help information'])
	#   ])
	# ])
	```
	```python
	from pyparam import params
	params.a = 1

	# add description for the program
	params._desc = 'A sample program.'

	def helpx(items):
		# add a section
		items['Java options'] = [('-java.io.tmpdir', 'dir', ['Tmpdir for java.'])]
		return items

	params._helpx = helpx
	params._parse()
	```
	```shell
	> python program.py
	```
	![helpx][16]

### Parameters from dict
-
	```python
	from pyparam import params
	params._prefix = '-'
	params._load({
		'opt1': '1',
		'opt2.required': True,
		'opt2.desc': 'This is option 2',
		'option2.alias': 'opt2',
		'opt3.required': True,
		'opt3.type': 'int',
		'opt3.desc': 'This is option 3',
	}, show = True)
	# show = False by default, params loaded from dict
	# will not be show in help page
	print(params._parse())
	```
	```shell
	python program.py
	```
	![fromdict][9]

	If an option is defined before loading, then the value and attributes will be overwritten.

### Parameters from file
-
	Parameters can also be loaded from a configuration file that is supported by [`python-simpleconf`][17]
	`sample.ini`
	```ini
	[default]
	opt1 = 1
	opt1.desc = 'This is option 1'
	[profile1]
	opt1 = 2
	```
	```python
	params._loadFile('sample.ini', profile = 'default')
	print(params.dict())
	# {'opt1': 1}
	# profile = 'profile1'
	# {'opt1': 2}
	```
### Different wrapper for `_parse` return value
-
	```python
	# python-box
	from box import Box
	from pyparam import params
	# don't exit if not arguments provided
	params._hbald = False
	params.opt = {'a': {'b': 1}}
	args = params._parse(dict_wrapper = Box)
	args.opt.a.b == 1
	```

### Sub-commands
-
	```python
	from pyparam import commands
	commands._prefix = '-'
	# common options for all commands
	commands._.workdir.desc      = 'The work directory.'
	commands._.workdir.required  = 'The work directory.'
	commands.show                = 'Shows information'
	commands.show.all            = False
	commands.show.all.desc       = 'Show all information'
	commands.show.depth          = 2
	commands.show.depth.desc     = 'Show the information on depth'
	# alias
	commands.list                = commands.show
	commands.run                 = 'Run script'
	commands.run.script.desc     = 'The script to run'
	commands.run.script.required = True
	print(commands._parse())
	```
	```shell
	> python program.py
	```
	![subcommand][12]
	```shell
	> python program.py -workdir ./workdir show -depth 3 -all
	('show', {'all': True, 'depth': 3}, {'workdir': './workdir'})
	#command,command options,          common options
	```




[1]: https://img.shields.io/pypi/v/pyparam.svg?style=flat-square
[2]: https://pypi.org/project/pyparam/
[3]: https://img.shields.io/travis/pwwang/pyparam.svg?style=flat-square
[4]: https://travis-ci.org/pwwang/pyparam
[5]: https://img.shields.io/codacy/grade/a34b1afaccf84019a6b138d40932d566.svg?style=flat-square
[6]: https://app.codacy.com/project/pwwang/pyparam/dashboard
[7]: https://img.shields.io/codacy/coverage/a34b1afaccf84019a6b138d40932d566.svg?style=flat-square
[8]: https://img.shields.io/pypi/pyversions/pyparam.svg?style=flat-square
[9]: https://raw.githubusercontent.com/pwwang/pyparam/master/docs/static/help.png
[10]: https://raw.githubusercontent.com/pwwang/pyparam/master/docs/static/short_long.png
[11]: https://raw.githubusercontent.com/pwwang/pyparam/master/docs/static/callback_error.png
[12]: https://raw.githubusercontent.com/pwwang/pyparam/master/docs/static/subcommand.png
[13]: https://raw.githubusercontent.com/pwwang/pyparam/master/docs/static/theme_blue.png
[14]: https://raw.githubusercontent.com/pwwang/pyparam/master/docs/static/theme_plain.png
[15]: https://raw.githubusercontent.com/pwwang/pyparam/master/docs/static/theme_custom.png
[16]: https://raw.githubusercontent.com/pwwang/pyparam/master/docs/static/helpx.png
[17]: https://github.com/pwwang/simpleconf