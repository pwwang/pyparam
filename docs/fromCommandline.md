A most common use of `pyparam` is to parse the values from command line. Parameters will be matched and values will be consumed until the end of the command line. Values will be finally compiled into a namespace.

!!! Note

	In this documentation, We are using `paramter` to specifically refer to the parameter that is defined with `pyparam`. For the items from command line, we call them `arguments`

## Argument name prefix

By default, the prefix is `auto`, meaning that for short names (length <= 1), it is `-`; while for long ones (length > 1), it is `--`.

You can specify your own prefix. Then all the names will be sharing the same prefix this way.

If you have values starting with the prefix, say `-1` as a value of an int paramter, to avoid that it's parsed as a name of an argument, you may need to attach the value to the name. For example, `-i-1`, `-i=-1` or `--int=-1` (see [Argument with attached value](#argument-with-attached-value)).

!!! Note

	We don't have any constraints on the `prefix`, but to reduce ambiguity, commonly used ones are recommended (i.e. `auto`, `-`, `--`, etc).

!!! Info

	Void prefix(`''`) is also supported, meaning that each element of the `sys.argv` is treated as a potential matched parameter. So the values should be attached to it (see [Argument with attached value](#argument-with-attached-value)).

	For example:
	```python
	params = Params(..., prefix='')
	params.add_param('i')
	parsed = params.parse(['i=1'])
	# parsed.i == 1
	```

## Argument with attached value

Users may pass an argument with attached value with it. For example:
```bash
prog -a1 -b=2 --count=3
```
Each of `-a1`, `-b=2`, `--count=3` is just one element of `sys.argv`. It is easy to deal with the latter two, since we have `=` as the delimiter. However, for the first one, we don't have some limitations to parse it as `param_name='a', param_value='1'`:

1. No type attached. For example, these cannot be detached: `-i:int1` and `--float:float1.1` (but these can: `-i:int=1` and `--float:float=1.1`).

2. prefix has to have length <= `1` or to be `auto`. For example, if you have:
   ```python
   params = Params(..., prefix='+')
   ```
   then `+a1` is also possible to be parsed as the above.
   If you have `prefx='--'` then, attached value without `=` will never be detached from the name, say: `--a1`, which will always be parsed as `param_name='a1', param_value=None`.

3. `a1` is not defined as a parameter and but `a` is.
   If you have `a1` defined as a parameter, then `-a1` will be anyway parsed as `param_name='a1', param_value=None`.
   If neither `a1` nor `a` is defined, a warning will be shown saying that `-a1` is an unknown argument.

4. In arbitrary mode (see [Arbitrary parsing](#arbitrary-parsing)), it doesn't require `a` to be defined if `a1` is not defined (it will be always `param_name='a1', param_value=None` if it is). Parameter `a` will be defined on the fly.

## Help argument

By default, once we hit one of `-h`, `-H` and `--help` from command line, `pyparam` will stop parsing, and print the help page.

You can change the help argument names by:
```python
# only with -h, --help
params = Params(..., help_keys='h,help')
# or
params = Params(..., help_keys=['h', 'help'])
```

When there is not arguments detected, meaning that there is only command name passed on the command line, the help page will print by default. Sometime when you want the program to get through instead of exit and print the help page, especially when all the paramters are optional and your program is able to run with those values. You can enable this by:
```python
params = Params(..., help_on_void=False)
```

## Positional argument

Positional argument is not enabled by default. You will have to add it by yourself:
```python
from pyparam import Params, OPTIONAL

params = Params()
params.add_param(POSITIONAL)
parsed = params.parse(['1', '2', '3'])
# parsed[POSITIONAL] == [1, 2, 3]
```

Maybe you have already noticed that the default type of the positional argument is `list:auto`. You can change it by `params.add_param(POSITIONAL, type=int)`. Then in the above case, the last 2 values (`'2'` and `'3'`) will be ignored and `parsed[POSITIONAL] == 1`

## Type overwritting

By default, type overwriting from the command line is disabled, unless your are resetting a list parameter (`--list:r 4 5`).

To enable type overwriting from command line, you can do:
```python
params.add_param('i', type=int, type_frozen=False)
```
Then from command line:
```sh
prog -i:float 1.1
```
is legal and the value of `i` will be a float number.

If type overwriting is enabled, the types for the parameters will be italic and in lowercase on help page.

## Arbitrary parsing

Arbitrary mode doesn't need the parameters to be pre-defined. They will be defined on the fly.

To enable arbitrary mode:
```python
params = Params(..., arbitrary=True)
parsed = params.parse()
```

For example:
```sh
prog -i 1 --float 2.1 --str:str 3
```
will produce a parsed namespace:
```python
Namespace(i=1, float=2.1, str="3")
```

You can play with this by running `$ python -m pyparam arbi ...`
