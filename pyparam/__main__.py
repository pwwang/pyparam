"""For users to test arbitrary parsing"""
import logging
import sys
from pathlib import Path

from rich import print

from . import Namespace, Params, defaults
from .utils import logger


defaults.CONSOLE_WIDTH = 100

params = Params(
    prog="pyparam",
    desc="""\
An exhibition showing all supported types of parameters and \
some features by running {prog}.

```python
# We can also insert code block in the description.
print('Hello pyparam!')
```

>>> # This is another example of code block using python console
>>> print('Hello pyparam!')""",
)

params.add_param(
    "d,debug", False, desc="Show the debug logging of the parsing process?"
)

predefined = params.add_command(
    [
        "p",
        "pred",
        "pd",
        "pdf",
        "predef",
        "predefined",
        "pre-defined",
        "pre-defined-args",
    ],
    desc="Some predefined arguments.",
    usage="""\
{prog} -i-1 --in . --py 1
{prog} --int=-1 --in . --py "(1,2,3)" -f0.1 -ccc
{prog} --int=-1 --in . --py "[1,2,3]" --float 0.1 --count 2
{prog} --int=-1 --in . --py True -b true --float 0.1
{prog} -i0 -b1 --choice=large
{prog} --int=-1 --bool false --float 0.1 --auto \
"{{\\\"a\\\": 1}}" --py "{{1, 2, 3}}" """,
)

predefined.add_param(
    "i, int",
    required=True,
    type=int,
    desc=[
        "An argument whose value will be casted into an integer.",
        "You can also try the short name with attached value: `-i1`.",
        "Negative values should be passed using `=`: ",
        "`-i-1` or `--int=-1`",
        "Same for other values starting with `-`. Default: 0",
    ],
)
predefined.add_param(
    "f, float",
    type_frozen=False,
    type=float,
    desc=[
        "An argument whose value will be casted into float.",
        "You can also try `--float=1e-3`",
        "You can even overwrite the type of the argument from command line by "
        "`--float:int=1`",
    ],
)
predefined.add_param(
    "b, bool",
    type=bool,
    desc=[
        "A boolean/flag argument. ",
        "If it is hit by itself, `True` will be used. However, it can consume "
        "one of following values: "
        "[true, TRUE, True, 1, false, FALSE, False, 0]",
    ],
)
predefined.add_param(
    "c, count",
    max=3,
    type="count",
    desc=[
        "A count argument, you can do -c, -cc, -ccc, etc.",
        "It must have a short name (`c` here for example). ",
        "You can also use it like an integer argument with long name. "
        "For example: --count 3",
        "The default value has to be `0` if specified. A max value can also "
        "be defined while adding this argument.",
    ],
)
predefined.add_param(
    "auto",
    desc=[
        "An argument whose value will be automatically casted.",
        "```python",
        "# Value received => Value/Type casted into",
        "'True', 'TRUE', 'true' => True",
        "'False', 'FALSE', 'false' => False",
        "'1', '2', '-1' => int",
        "'1.1', '2.0', '-1.0' => float",
        '\'{{"a": 1}}\' => {{"a": 1}} # json',
        "```",
        "If you don't want the value to be casted. Declare the argument with "
        "type `str`",
    ],
)
predefined.add_param(
    "in",
    type="path",
    required=True,
    desc=[
        "An argument whose value will be casted into `pathlib.Path`.",
        "Since the argument name is a python keyword, you may not be able to "
        "fetch the value by:",
        "```python",
        "parsed = params.parse()",
        "parsed.in",
        "# you can do parsed['in'] instead.",
        "```",
        "You can use a callback here to check if the path exists:",
        ">>> def callback(path):",
        ">>>    if not path.exists():",
        ">>>        # You can also return the error using lambda",
        ">>>        raise ValueError('Path does not exist.')",
        ">>>    return path",
    ],
    callback=(
        lambda path: ValueError("Path does not exist.")
        if not path.exists()
        else path
    ),
)
predefined.add_param(
    "py",
    required=True,
    type="py",
    desc=["Value will be evaluated using `ast.literal_eval`"],
)
predefined.add_param(
    "str",
    default="size",
    type="str",
    desc=["Value will be kept anyway as a string."],
)
predefined.add_param(
    "json",
    type="json",
    default="{}",
    desc=["Value will be converted using `json.loads`"],
)
predefined.add_param(
    "choice",
    type="choice",
    desc=[
        "One of the choices: small, medium and large.",
        "Callback can also be apply to modify the value:",
        ">>> def callback(value, all_values):",
        ">>>    # Use the value of argument '--str'",
        ">>>    return f'{{value}} {{all_values.str}}'",
    ],
    choices=["small", "medium", "large"],
    default="medium",
    callback=(lambda value, all_values: f"{value} {all_values.str}"),
)
predefined.add_param(
    "list",
    default=[1, 2, 3],
    type=list,
    desc=[
        "List/Array argument.",
        "You can pass the values one by one like this: `--list 1 2 3`.",
        "Or like this: --list 1 --list 2 --list 3",
        "List argument is incremental, meaning the values will be added to "
        "the values. To stop doing that, you can direct users to reset it "
        "using: ",
        "`--list:reset 4 5 6` or ",
        "`--list:reset 4 --list 5 --list 6`",
        "You can also set a subtype for list elements, including the "
        "scalar types. "
        "For exapmle: ",
        "`--list:list:bool 0 1 0` will produce [False, True, False].",
    ],
)

nsparams = params.add_command(
    "n, nsparams",
    help_on_void=False,
    desc=[
        "Namespace parameters. ",
        "No required arguments under this command, "
        "`help_on_void` is set to False.",
        "To bring up the help page, try arguments `-h/--help/-H`",
    ],
)
nsparams.add_param(
    "config.nlayers", type="int", default=8, desc=["Number of layers."]
)
nsparams.add_param(
    "config.num-heads", type="int", default=8, desc=["Number of heads."]
)
# give some description to put it on help page
nsparams.add_param(
    "config.nested, config.nt",
    type="ns",
    desc="""\
Nested configurations under config.
You can also apply callback to change the value of the whole namespace:
```python
def callback(value, all_values):
    value.gpus += all_values.config.nlayers
    return value
```""",
    callback=(
        lambda value, all_values: setattr(  # type: ignore
            value, "gpus", value.gpus + all_values.config.nlayers
        )
        or value
    ),
)
nsparams.add_param(
    "config.nested.gpus",
    type="int",
    default=1,
    desc=["Number of GPUs to use."],
)

nested_cmd = params.add_command("nested-cmd", desc="Nested commands")
nested_cmd2 = nested_cmd.add_command(
    "nested-cmd2", desc="A command of `nested-cmd`"
)


params.add_command(
    "a, arbi, arbitrary",
    desc="No predefined arguments, but you can "
    "pass arbitrary arguments and see how "
    "`pyparam` parses them",
    arbitrary=True,
)

fromfile = params.add_command(
    "f, fromfile",
    desc="""\
Load parameter definition from file.
You can load parameter definitions from any file type that \
`python-simpleconf` supports.
For example, a toml file:

```toml
[params.arg]
desc = "An argument"
```

See `example.toml` in the repo.
""",
)
fromfile.from_arg("file", desc="The file to load parameters from.")

complete = params.add_command(
    "complete",
    desc="""\
Generate shell code for completions.

For bash:
```sh
$ python -m pyparam complete --shell bash --module >> ~/.profile
```

For zsh:
```sh
$ python -m pyparam complete --shell zsh --module >> ~/.zprofile
```

For fish:
```sh
$ python -m pyparam complete --shell fish --module \\
    >> ~/.config/fish/completions/python.fish
```
""",
)
complete.add_param(
    "shell",
    required=True,
    type="choice",
    choices=["bash", "fish", "zsh"],
    desc="The shell where the program will be running. " "One of {choices}.",
)
complete.add_param(
    "script", default=False, desc="Generate shell code for `python <prog>`"
)
complete.add_param(
    "module", default=False, desc="Generate shell code for `python -m <prog>`"
)
complete.add_param(
    "py,python",
    default=Path(sys.executable).name,
    desc="The python executable.",
)
complete.add_param(
    "dir",
    type="dir",
    default=Path(__file__).parent,
    desc="This does nothing but just show you "
    "how directory completion works.",
)
complete.add_param(
    "choice",
    type="choice",
    choices=["xsmall", "small", "medium", "large", "xlarge"],
    desc="This does nothing but just show you " "how complete callback works.",
    complete_callback=None,
)


def vars_ns(ns, depth=None):
    """Get the vars of a namespace"""
    ret = vars(ns)
    for key, val in ret.items():
        if (depth is None or depth > 0) and isinstance(val, Namespace):
            ret[key] = vars_ns(val, None if depth is None else depth - 1)
    return ret


def main():
    """Main entry"""
    parsed = params.parse()

    if parsed.debug:
        logger.setLevel(logging.DEBUG)
        params.parse()

    if parsed.__command__ == "complete":
        print(
            params.shellcode(
                shell=parsed.complete.shell,
                python=parsed.complete.python
                if parsed.complete.script or parsed.complete.module
                else None,
                module=parsed.complete.module,
            )
        )
    else:
        print()
        print("Arguments passed in:")
        print()
        print(vars_ns(parsed))


if __name__ == "__main__":
    main()
