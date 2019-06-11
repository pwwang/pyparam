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