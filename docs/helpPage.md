## Themes
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

## Manipulation of the message
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

[13]: https://raw.githubusercontent.com/pwwang/pyparam/master/docs/static/theme_blue.png
[14]: https://raw.githubusercontent.com/pwwang/pyparam/master/docs/static/theme_plain.png
[15]: https://raw.githubusercontent.com/pwwang/pyparam/master/docs/static/theme_custom.png
[16]: https://raw.githubusercontent.com/pwwang/pyparam/master/docs/static/helpx.png
