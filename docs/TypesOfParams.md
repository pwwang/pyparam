
A parameter is supposed to be defined/added by `params.add_param(...)` or `command.add_param(...)`, where `command` is the command added by `params.add_command(...)`.

## Parameter names

We are not distinguishing name and its aliases for a parameter. That means basically all names for a parameter are treated equally. The only difference is the order when they are displayed in the help page, where they are sorted by their length.

Supposingly, when add a parameter, any given name should not be registered before. Meaning that there should not be any parameters or commands with any of the given names added before.

!!! Note

    Why a name should not be shared by a parameter and a command?

    That's because the parsed results are stored in a `Namespace`. You can't tell whether `ns.abc` is to get the value of the parameter `abc` or the values of parameters that are under command `abc`.

However, you can overwrite existing parameters or commands by `params.add_param(..., force=True)`. By doing this, you should know what you will lose.

## Parameter types

You can specify a type explictly by `params.add_param(..., type='int')`, or if you provide a default value for the parameter, the type will be automatically inferred from the default value:

| Example of default value | Parameter type inferred |
|--------------------------|-------------------------|
| `1` | int |
| `1.1`, `5e-2` | float |
| `"foo"` | str |
| `True`, `False` | bool |
| `pathlib.Path('.')` | path |
| `{"foo": "bar"}` | json |
| `[1, 2, 3]` | list:int |
| `["foo", "bar", 1]` | list |
| otherwise | auto |

For `int`, `float`, `str`, `bool` and `list`, you can specify the type using the type itself instead of its name. For example, you can do `params.add_param('foo', type=int)` instead of `params.add_param('foo', type='int')`.

### int/float/str paramter

Alias: `i/f/s`.
Default value if not specified: `0/0.0/""`

Values passed in will be casted into corresponding types.

### auto paramter

Alias: `a`.
Default value if not specified: `None`

Values will be casted automatically according to the values.

For example:

| Value (str) | Casted value |
|-------|--------------|
| `"True"`, `"TRUE"`, `"true"` | `True` |
| `"False"`, `"FALSE"`, `"false"` | `False` |
| `"1"` | `1` |
| `"0.05"`, `"5e-2"` | `0.05` |
| `"{\"foo\": \"bar\"}"` | `{"foo": "bar"}` |

### bool paramter

Alias: `b/flag`
Default value if not specified: `False`

Similar as `int/float/str` parameters. The difference is that, when it is followed by a value that can be casted into a bool value, it consumes it. Otherwise, it doesn't. For example, following will be parsed into the same result:

```sh
$ prog -b
$ prog -b true
```

### count paramter

No alias.
Default value if not specified: `0`

A count parameter is actually an int parameter, with a short name with length = 1 required (say `v`). So that we can do `-vvv` from the command line.

A count parameter requires default value to be `0`. In the above case, `-vvv` will be parsed as value `3`. Users can also use the normal way to pass the value to a count parameter: `-v 3`, or if it has a long name: `--verbose 3`.

You can also specify a maximum value for the count parameter. For example: `params.add_param('v, verbose', type='count', max=3)` will raise an error when `-vvvv` received.

### path parameter

Alias: `p`
Default value if not specified: `None`

THe value of a path parameter will be automatically converted into a `pathlib.Path` object.

!!! Tip

    It will not check the existence of path by default.

    To do that, you will need to use callback. For example:
    ```python
    def callback(path):
        if not path.exists():
            raise ValueError("Path does not exist.")
        return path
    params.add_param('input-file',
                     type='path',
                     required=True,
                     callback=callback)
    ```

    See how callback works at [parameter callbacks](#paramter-callbacks)

### py paramter

No alias.
Default value if not specified: `None`

The value will be evaluated by `ast.literal_eval`.

### json paramter

Alias: `j`
Default value if not specified: `None`

The value will be converted using `json.loads`

### choice paramter

Alias: `c`
Default value if not specified: The first element of `choices`

The value is required to be one of the given values. To provide choices to choose:

`params.add_param('choice', choices=["small", "medium", "large"])`

Default is `small` if not provided.

### list paramter

Aliases: `l`, `array`
Default value if not specified: `[]`

A list parameter keeps consuming the value followed by until it hits another argument in command line.
For example: `--array 1 2 3` will produce `[1, 2, 3]` for `array`, while `--array 1 --array 2 --array 3` does the same.

You would like to provide a default value for a list parameter, say `[1, 2, 3]`. When it receives `--array 4` from command line, the value will accumulated and become `[1, 2, 3, 4]`. Sometimes, users may want to start a new array for that parameter, meaning that only `[4]` is desired by passing `--array 4`. In such a case, users can do `--array:reset 4` or `--array:r 4`. To accumulate more values, they can do `--array:r 4 5 6` or `--array:4 --array 5 --array 6`.

A list parameter can have a subtype for the element of the list to be casted to. A subtype should be any of the above (scalar) types, not including `list`. By default, the subtype is `auto`. You can specify one explictly by: `params.add_param('array', type='list:str')`, then `--array 1 2 3` will produce `['1', '2', '3']` instead of `[1, 2, 3]`.

### namespace parameter

Name: `ns`, alias: `namespace`

A namespace parameter is a special parameter that does not consume or receive any values. It only serves as a namesapce for other paramters.

A namespace parameter can be defined explictly or implicitly. If you define a parameter like this: `params.add_param('config.ncores', ...)` then the namespace parameter `config` is implied. You may also define a namespace parameter explictly:
```python
params.add_param('config', type='ns', desc='A collection of configurations')
```

!!! Warning

    A namespace parameter should be defined before the parameters under it.

If a namespace parameter has aliases, the parameters under it will expand their names in the namespace part with all names of this namespace parameter.

For example:
```python
params.add_param('c, config', type='ns')
param = params.add_param('c.ncores', type=int, desc='Number of cores')
# param.names == ['c.ncores', 'config.ncores']
```

## Parameter descriptions

To add descriptions for a parameter: `params.add_param(..., desc=...)`. Descriptions can be given as a single string or a list of strings. The difference is that, in the help page, the single string will be automatically wrapped according to the given console width; while each element of the list will be ensured to be put in a new line. If each element is beyond the width, it will be wrapped as well.

For example, you can't control where it will be wrapped by `params.add_param(..., desc='I might be a very very long description')`. However, you can break it down and specify it as a list of some short strings: `params.add_param(..., desc=['I might be a very ', 'very long description'])`. In this way, the description is ensured to be broken between the two `very`s. If the width is wider than the two strings, they won't be wrapped any more. And they will automatically if the width is narrower.

You can also use some placeholders in the description, including the keyword argument from `params.add_param(...)`. For example: `params.add_param('choice', default=1, choices=[1, 2, 3], desc='One of {choices}')` will give you `One of [1, 2, 3]`.

You can insert inline code or code blocks in the description.

For inline code, they should be quoted by one or more backticks. In most cases, it should be single backtick. However, when you have backtick inside your inline code, you may want to use multiple.

For code blocks, you can do `python console` way:

<code>
\>>> print('Hello pyparam!')
</code>


Or the markdown way:

<code>
\```python<br />
print('Hello pyparam!')<br />
\```
</code>

### Add default value in description

Default value is automatically added for optional (`required=False`) and non-namespace (`type!='ns'`) parameters. It will be added in the format of `Default: xxx` and appended to the first element of the description list.

For example:
```python
params.add_param('i', desc=[
    'This is an int argument.',
    'More details about it.'
])
```
will produce:

```
This is an int argument. Default: 0
More details about it.
```
However, a description of a single string will have default value appended to the end.

You can also add your own default value to description, by `Default: xxx` or `DEFAULT: xxx` to any element of the description list, or the single description string. Once detected, the default value specified by `params.add_param(..., default=xxx)` will not be added again.

This opens oppotunities for you to place and customize the default value shown in help page by yourself.

In the above example, if you want to put the default value in a new line rather than append it to the first line:
```python
params.add_param('i', desc=[
    'This is an int argument.',
    'Default: 0',
    'More details about it.'
])
```

!!! Tip

    If you have newlines in the default value, the whole default will be put in a new line. And from the second line on, it will be indented.

    For example:
    ```python
    params.add_param('s', default="1\n2")
    ```
    will produce
    ```
    No description.
    Default: 1
             2
    ```

    This is helpful for you to align the default value when you have complex ones.

## Parameter callbacks

Parameters, including namespace parameter, can have callbacks to modify their values after parsing. The results from the callbacks can be arbitrary, meaning the value from the result namespace can be in different type as specified.

Exceptions can be raised from callbacks, and they will be interpreted as errors in the help page. To allow exceptions in lambda functions, instead of raise, you can also return an `Exception` object if error happens.

Here are some examples to show how callbacks work:

- Check if value of path parameter exists

    ```python
    def callback(path):
        if not path.exists():
            raise ValueError('Path does not exist.')
        return path

    params.add_param('in-file', type='p', callback=callback)
    # or alternatively
    params.add_param('in-file', type='p',
                     callback=lambda path: ValueError('Path does not exist.')
                     if not path.exists() else path)

    parsed = params.parse(['--in-file', '/path/not/exists/'])

    # Error:   --in-file: Path does not exist.
    ```

- Modify count value

    Since the default value is required to be `0`, you may modified the value as you like:
    ```python
    params.add_param('v', type='count')

    parsed = params.parse('-vvv', callback=lambda val: val * 10)
    # parsed = Namespace(v=30)
    ```

- Modify a namespace value

    ```python
    params.add_param('config', type='ns',
                     callback=lambda val: val.ncores*val.mem)
    params.add_param('config.ncores', type=int)
    params.add_param('config.mem', type=int)

    parsed = params.parse(['--config.ncores', '4', '--config.mem', '1024000'])
    # parsed.config == 4 * 1024000
    ```
    See [Using the parsed values](../useTheValues/) for more details on how to use the namespace values attached to a namespace parameter.

- Modify value using other values

    ```python
    params.add_param('pool', type=list, default=['small', 'medium', 'large'])
    params.add_param('choice', type='c', default=0, choices=[0, 1, 2],
                     callback=lambda val, allvals: allvals.pool[val])
    parsed = params.parse(['--choice', '1'])
    # parsed.choice == 'medium'
    ```
