## Basic usage

`examples/basic.py`
```python
from pyparam import params
# define arguments
params.version      = False
params.version.desc = 'Show the version and exit.'
params.quiet        = False
params.quiet.desc   = 'Silence warnings'
params.v            = 0
# verbose option
params.v.type = 'verbose'
# alias
params.verbose = params.v
# list/array options
params.packages      = []
params.packages.desc = 'The packages to install.'
params.depends       = {}
params.depends.desc  = 'The dependencies'

print(params._parse())
```
```shell
> python example/basic.py
```
![help][9]

```shell
> python examples/basic.py -vv --quiet \
	--packages numpy pandas pyparam \
	--depends.completions 0.0.1
{'h': False, 'help': False, 'H': False,
 'v': 2, 'verbose': 2, 'version': False,
 'V': False, 'quiet': True, 'packages': ['numpy', 'pandas', 'pyparam'],
 'depends': {'completions': '0.0.1'}}
```

!!! Note
	Default help options are `h`, `help` and `H`, if values are parsed, those values should all be `False`. In later this document, these items will not be shown.

## Fixed prefix
By default, prefix is set to `auto`, which means `-` for short option and `--` for long options.

`examples/fixedPrefix.py`
```python
from pyparam import params
params._prefix = '-'
# same as basic.py
```
```shell
> python program.py -opt2 1 -opt3 4 -opt1 5
{'h': False, 'help': False, 'H': False, 'opt1': '5', 'opt2': 1, 'o': 1, 'opt3': 4}
```

## Callbacks
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

## Type redefinition
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

## List/Array options
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

## Positional options
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

## Dict options
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

## Arbitrary parsing
Parse the arguments without definition
```python
print(params._parse(arbi = True))
```
```shell
> python program.py -a 1 -b:list 2 3 -c:dict -c.a.b 4 -c.a.c 5 -d:list:list 6 7 -d 8 9
{'h': False, 'help': False, 'H': False,
 'a': 1, 'b': [2, 3], 'c': {'a': {'b': 4, 'c': 5}}, 'd': [['6', '7'], ['8', '9']]}
```

[9]: https://raw.githubusercontent.com/pwwang/pyparam/master/docs/static/help.png
[11]: https://raw.githubusercontent.com/pwwang/pyparam/master/docs/static/callback_error.png
