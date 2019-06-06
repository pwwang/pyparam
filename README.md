# pyparam
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