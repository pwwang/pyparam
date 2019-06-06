# pyparam
[![pypi][1]][2] [![travis][3]][4]

Powerful parameter processing

## Installation
`pip install pyparam`

## Usage
### Command line argument parsing
`program.py`
```python
from param import params
params.a.desc = 'Option a'
print(params.parse())
```
```shell
> program.py -a 1
{'a': 1}
```

[1]: https://img.shields.io/pypi/v/pyparam.svg?style=flat-square
[2]: https://pypi.org/project/pyparam/
[3]: https://img.shields.io/travis/pwwang/pyparam.svg?style=flat-square
[4]: https://travis-ci.org/pwwang/pyparam