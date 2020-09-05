## Loading parameters from a dict

You can skip all those `add_param` and `add_command` calls, and load the parameter/command definition from a python dictionary.

There are two way to do that:

### Express dict

The express way is a depth 1 dictionary where all the keys are flattened.
```python
from pyparam import Params

params_def = {
    "i": 1, # default value
    "i.aliases": ["int"],
    "i.type": "int",
    "i.desc": ["An int parameter"],
    # ...
    "f": 1.0,
    "f.aliases": ["float"],
    "f.type": "float",
    "f.desc": ["A float parameter"]
}

params = Params()
params.file_dict(params_def)
# This does the same as
params.add_param("i,int", default=1, type=int, desc=["An int parameter"])
params.add_param("f,float", default=1.0, type=float, desc=["A float parameter"])
```

Express dict has some limitations:

1. No sub-command specifications are allowed
2. No namespace parameters

### Full specification dict

One can use the full specification dictionary to have sub-command and namespace parameter definitions enabled:

```python

params_def = {
    "params": {
        "i": {
            "default": 1,
            "aliases": ["int"],
            "type": "int",
            "desc": ["An int parameter"]
        },
        "f": {
            "default": 1.0,
            "aliases": ["float"],
            "type": "float",
            "desc": ["A float parameter"]
        }
    },
    "commands": {
        "cmd": {
            # aliases: [...]
            # prefix: ...
            "params": {
                "c": {
                    "default": "medium",
                    "type": "choice",
                    "choices": ["small", "medium", "large"]
                },
                "config": {
                    "type": "ns",
                    "desc": "A set of configurations"
                },
                "config.ncores": {
                    "default": 4,
                    "desc": "Number of cores"
                }
            }
        }
    }
}
params.from_dict(params_def)
parsed = params.parse()
```

This:
```sh
prog -i 1 -f 2.0 cmd -c large --config.ncores 1
```
will produce:
```python
Namesapce(__command__='cmd',
          i=1,
          f=2.0,
          cmd=Namesapce(c='large', config=Namesapce(ncores=1)))
```

### Hiding parameters from help page

If you don't want a parameter to be shown in help page, especially when it not required, just pass `show=False` to it. In the dictionary, you can just do:
```python
params_def = {
    "x": 1,
    "x.show": False
}
```
Or with full specification:
```python
params_def = {
    "params": {
        "x": {
            "default": 1,
            "show": False
        }
    }
}
```

Or if you want to hide all the parameters from a dict except those with `show=True` explictly:
```python
params.from_dict(params_def, show=False)
```

## Loading from a configuration file

Parameters can also be loaded from a configuration file that is supported by [`python-simpleconf`][1]

Those configuration files will be first read and turned into python dictionary, and then parameter definitions will be loaded using `params.from_dict`.

There is the `toml` file that are the same as the above dict examples.

- Express:

    ```toml
    i = 1
    "i.aliases" = ["int"]
    "i.type" = "int"
    "i.desc" = ["An int parameter"]
    # ...
    f = 1.0
    "f.aliases" = ["float"]
    "f.type" = "float"
    "f.desc" = ["A float parameter"]
    ```

- Full specification

    ```toml
    [params.i]
    default = 1
    aliases = ["int"]
    type = "int"
    desc = "An int parameter"

    [params.f]
    default = 1.0
    aliases = ["float"]
    type = "float"
    desc = ["A float parameter"]

    [commands.cmd.params.c]
    default = "medium"
    type = "choice"
    choices = ["small", "medium", "large"]

    [commands.cmd.params.config]
    type = "ns"
    desc = "A set of configurations"

      [commands.cmd.params."config.ncores"]
      default = 4
      desc = "Number of cores"
    ```

### Loading from a configuration file specified by a command line argument

You may also ask user to specify a configuration file to load parameter/command definitions from.

Something like:
```sh
prog --config-file params_def.toml -i 1 -f 2.0 ...
```
Then the parameter/command definitions will be loaded from `params_def.toml`.

To do it:
```python
params.from_arg('config-file')
```

First, `pyparam` will scan the `sys.argv` to see if any item matches `--config-file`. If it does, then the next item (`params_def.toml`) will be used.

To show the paramter `config-file` in the help page, you can also specify some desciptions to it:
```python
params.from_arg('config-file', desc=..., group=...)
```

To use full configuration of a parameter, one can also add it as a parameter first:
```python
configfile = params.add_params('config-file', ...)
# then
params.from_arg(configfile)
```

## Skipping command line argument parsing

`pyparam` can also work as a value holder, which does not parse anything from the command line, but just use the predefined values. This requires all the parameters are optional and no command has been defined.

For example:
```python
params.add_param('i', default=0)
params.values() # Namespace(i=0)
```

Parameter callbacks are still applicable here.

[1]: https://github.com/pwwang/simpleconf
