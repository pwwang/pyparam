# pyparam
[![pypi][1]][2] [![travis][3]][4] [![codacy quality][5]][6] [![codacy quality][7]][6] 

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
[5]: https://img.shields.io/codacy/grade/a34b1afaccf84019a6b138d40932d566.svg?style=flat-square
[6]: https://app.codacy.com/project/pwwang/pyparam/dashboard
[7]: https://img.shields.io/codacy/coverage/a34b1afaccf84019a6b138d40932d566.svg?style=flat-square