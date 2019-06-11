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


[9]: https://raw.githubusercontent.com/pwwang/pyparam/master/docs/static/help.png