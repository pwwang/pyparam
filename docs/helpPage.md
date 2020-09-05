
## Grouping parameters/commands

On the help page, parameters/commands are put in groups. You can specify the group for a parameter or command by `params.add_param(..., group=xxx)` or `params.add_command(..., group=xxx)`

If not specified, we have default groups assigned for them

### Default group

Optional parameters will be in group `OPTIONAL OPTIONS`, and required parameters will be in group `REQUIRED OPTIONS`.

For a namespace parameter, if any paramters under it is required, then the namespace parameter is required, otherwise it optional. Those parameters under a namespace parameter will be grouped as something like `OPTIONAL OPTIONS UNDER --config`.

Sub-commands are grouped into `COMMANDS`

## Manipulating help page

You are able to modify the help page yourself. Just pass a callback funtion to `Params`:
```python
params = Params(..., help_callback=...)
```

A help callback function takes only one argument, which is a `OrderedDiot` object (A dot-notation enabled `OrderedDict` by [`diot`][1]). Each key is a section title and value is the corresponding content of that section. The content be one of `HelpSectionPlain`, `HelpSectionUsage` and `HelpSectionOption` objects. They are basically subclasses of `list`. The elements of first two are just strings; while they are 2-element tuples for the last one. Those two elements are lists of parameter names/types and descriptions.

Here are the examples on how you can manipulate the help page.

- Without callback:
    ```python
    from pyparam import Params
    params = Params(prog='pyparam')
    params.add_param('i')
    params.print_help()
    ```

    DESCRIPTION:
      No description

    USAGE:
      pyparam [OPTIONS]

    OPTIONAL OPTIONS:
      -i <AUTO>                        - No description. Default: None

- Adding a section
    ```python
    from pyparam import Params
    from pyparam.help import HelpSectionPlain
    def help_callback(assembled):
        assembled.SEE = HelpSectionPlain(
            ['See: https://github.com/pwwang/pyparam']
        )

    params = Params(prog='pyparam', help_callback=help_callback)
    # add paramters and print help
    ```

    ```
    DESCRIPTION:
      No description

    USAGE:
      pyparam [OPTIONS]

    OPTIONAL OPTIONS:
      -i <AUTO>                        - No description. Default: None

    SEE:
      See: https://github.com/pwwang/pyparam
    ```

    You can also insert a section to a certain position:
    ```python
    assembled.insert(0, "SEE", HelpSectionPlain(...))
    # or insert before or after a section
    assembled.insert_after('DESCRIPTION', "SEE", HelpSectionPlain(...))
    ```

    To add a option section (with option name, type and descriptions):
    ```python
    from pyparam.help import HelpSectionOption
    def help_callback(assembled):
        assembled['EXTRA OPTIONS'] = HelpSectionOption([
            (['-i, --int <INT>'], ['An int paramter', 'Default: 0']),
            (['-f, --float <FLOAT>'], ['An float paramter', 'Default: 0.0']),
        ])
    ```

- Removing a section:
    ```python
    del assembled['DESCRIPTION']
    ```

- Modify a section:
    ```python
    # it is just a list!
    assembled.DESCRIPTION[0] = 'Awesome program!'
    ```

    ```
    DESCRIPTION:
      Awesome progrom!

    USAGE:
      pyparam [OPTIONS]

    OPTIONAL OPTIONS:
      -i <AUTO>                        - No description. Default: None
    ```

## Changing the size of help page

Default sizes of the help page are defined in `pyparam.defaults`.

To change them:
```python
from pyparam import defaults

# Total width of the help page
# change it to None to spread the help page with full terminal width
defaults.CONSOLE_WIDTH = 100
# indention for the contents of each section
defaults.HELP_SECTION_INDENT = 2
# The width of the name/type part in HelpSectionOption
defaults.HELP_OPTION_WIDTH = 34
# For exapmle:
#     OPTIONAL OPTIONS:
#       -i, --int <INT>                  - An integer argument. Default: 0
#     |<-------------------------- CONSOLE_WIDTH ----------------------------------->|
#   ->||<-  HELP_SECTION_INDENT
#     |<----- HELP_OPTION_WIDTH ------->|
```

## Theming

For now, there is one builtin theme: `default` (more to come).
But you can specify your own theme by:
```python
from rith.theme import Theme
params = Params(..., theme=Theme({
    # The section title
    'title': "bold cyan",
    # Highlight program name
    'prog': "bold green",
    # Highlight default value in parameter description
    'default': "magenta",
    # Highlight option names
    'optname': "bright_green",
    # Highlight option types when type overwriting is enabled
    'opttype': "blue italic",
    # Highlight option types when it is disabled
    'opttype_frozen': "blue"
}))
```

See more details in [rich's documentation][2].


[1]: https://github.com/pwwang/diot
[2]: https://rich.readthedocs.io/en/latest/style.html#style-themes
