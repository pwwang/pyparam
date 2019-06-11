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
> python examples/fixedPrefix.py  -vv \
	-packages numpy pandas pyparam \
	-depends.completions 0.0.1 --quiet
Warning: Unrecognized positional values: '--quiet'
{'v': 2, 'verbose': 2, 'version': False,
 'V': False, 'quiet': False, 'packages': ['numpy', 'pandas', 'pyparam'],
 'depends': {'completions': '0.0.1'}}
```

## Option types
`pyparam` supports following types. We will see how these types are used to define an option or overwrite the type of an option on command line.

|Type|Alias|Meaning|
|----|-----------|-------|
|`auto`|`a`|Used when type is not define. Values will be converted automatically|
|`int`|`i`|Values will be converted into an `int`|
|`float`|`f`|Values will be converted into a `float`|
|`bool`|`b`|Values will be converted into a `bool`|
|`NoneType`|`none`, `n`|Values will be converted into `None`|
|`str`|`s`|Values will be converted into a `str`|
|`dict`|`d`, `box`|Values will be converted into a `dict`|
|`list`|`l`, `array`|Values will be converted into a `list`|
|`verbose`|`v`, `verb`|Values will be parsed in `verbose` mode|
|`python`|`p`, `py`|Values will be converted using `ast.literal_eval`|
|`reset`|`r`|Reset a `list`, a `list:list` or a `dict`|

## Auto options
If a type of an option is not defined, then `auto` will be used. While parsing, the value will be cased into:
1. `None` if value is either `"none"`, `"None"` or `None` itself.
2. an `int` if value matches an integer
3. a `float` if value matches a float
4. `True` if value is in `[True , 1, 'True' , 'TRUE' , 'true' , '1']`
5. `False` if value is in `[False, 0, 'False', 'FALSE', 'false', '0', 'None', 'none', None]`
6. a value casted by `ast.literal_eval` if it starts with `py:` or `repr:`
7. a string of the value.

`examples/autotype.py`
```python
from pyparam import params
params.a.desc = 'This is an option with `auto` type.'
print(params._parse())
```

```shell
python examples/autotype.py -a none
{'a': None}

python examples/autotype.py -a 1
{'a': 1}

python examples/autotype.py -a 1.1
{'a': 1.1}

python examples/autotype.py -a true
{'a': True}

python examples/autotype.py -a false
{'a': False}

python examples/autotype.py -a 'py:{"x": 1}'
{'a': {'x': 1}}

# you want to pass everything as str
python examples/autotype.py -a:str 1
{'a': '1'}
```

## List/Array options

```shell
> python examples/basic.py --packages pkg1 pkg2 pkg3 # or
> python examples/basic.py --packages pkg1 --packages pkg2 --packages pkg3
# other values not shown
{'packages': ['pkg1', 'pkg2', 'pkg3']}
```

Default values:
```python
params.packages = ['required_package']
```
```shell
> python examples/basic.py --packages pkg1 pkg2 pkg3
'packages': ['required_package', 'pkg1', 'pkg2', 'pkg3']
```

Reset list options
```shell
# we don't want to install the "required_package"
> python examples/basic.py --packages:reset pkg1 pkg2 pkg3
'packages': ['pkg1', 'pkg2', 'pkg3']
```

Elements are casted using `auto` type by default:
```shell
> python examples/basic.py --packages:reset pkg1 pkg2 true
'packages': ['pkg1', 'pkg2', True]
```

You may force it all strings after reset:
```shell
> python examples/basic.py --packages:reset --packages:list:str pkg1 pkg2 true
'packages': ['pkg1', 'pkg2', 'true']
# or define the subtype:
# params.packages.type = 'list:str'
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

## Callbacks
Callbacks are used to modified/check option values.

`examples/callback_check.py`
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
python examples/callback_check.py -o /path/not/exists/outfile
```
![callback_error][11]

Modify value with other options:

`examples/callback_modify.py`
```python
from pyparam import params
params.amplifier = 10
params.number.type = int
params.number.callback = lambda param, ps: param.setValue(
	param.value * ps.amplifier.value)
print(params._parse())
```
```shell
> python examples/callback_modify.py -amplifier 100 -number 2
{'amplifier': 100, 'number': 200}
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
