
## Root command

Root command is instantiated like `params = Params(...)`, and sub-commands are added like `params.add_command(...)`. Both root command and sub-commands are objects of class `Params`.

Root command doesn't have names, but it does have `prog` to define the program name:
```python
params = Params(..., prog='pyparam')
```
If not given, `sys.argv[0]` will be used.

`prog` will be used to format the description and the usage of the program.

### Description

Like paramter description, you can provide a single string or a list of strings as the description. And it acts the same as the paramter description in terms of differences between single string and list of strings.

You can also code blocks as we do for parameter descriptions. See [Parameter descriptions](../TypesOfParams/#parameter-descriptions).

### Usage

You can specify some example usages for the program. A single string or list of strings acts as the description. You can also use `{prog}` as a placeholder for the program name.

By default, `pyparam` generates default usages for the program. It literally list all the required parameters and merge all optional ones as `[OPTIONS]`.

## Sub-commands

Sub-commands act very similarly as the root command. But unlike the root command, they do have names, which are used from themselves to be detected from the command line. A typical way to add a command is: `params.add_command('command, command_alias', ...)` or `pyparam.add_command(['command', 'command_alias'], ...)`

A sub-command can have sub-commands, too. Just add some commands to the sub-command:
```python
command1 = params.add_command('cmd1, command1', ...)
subcommand1 = command1.add_command('subcmd1, subcommand1', ...)
```

You don't have to call `parse()` for sub-commands, the root command will do it once `params.parse()` is called. All descades of sub-commands' `parse()` method will be called automatically.

The attribute `prog` for a sub-command is its parent command's prog plus `[OPTIONS]` if any and plus the longest name of the sub-command. You can replace this by `params.add_command(..., prog='prog command')`.

Their attributes are independent of their parent command, but once absence, they will be inherited from the parent command. For example:
```python
params = Params(..., prefix='+')
command = params.add_command('command')
# command == '+'
```
You can change this by:
```python
params = Params(..., prefix='+')
command = params.add_command('command', prefix='-')
```
Then with the parameters being added:
```python
params.add_param('i')
command.add_param('i')
parsed = params.parse()
```
This:
```sh
$ prog +i 1 command -i 2
```
will produce
```
Namespace(__command__='command',
		  i=1,
		  command=Namespace(i=2))
```

## Command reuse

To reuse a command, you can define a command in either way below:
```python
from pyparam import Params
# root command
params = Params()
command = params.add_command('cmd')
# or
command = Params('cmd')
```
Then add it by:
```python
params.add_command(command)
```
In such a case, other arguments of `params.add_command` will be ignored, except `force` and `group`.

!!! Note

	Unlike reuse of parameters, the `command` here is not copied. This means any changes you make on `command` will reflect on `params.commands['cmd']`

## Help command

One can invoke sub-command's help page by:
```sh
prog help command
```
Where help is also a sub-command, which means you can invoke the help page of the help sub-command.

You can change the default help command by `params.add_command(..., help_cmds='show')`. Then the invoke command is like:
```sh
prog show command
```

### Modifying help command

Sometimes, you may want to modify the help command, for example, its group showing in the help page.
To do this, you need to define a callback and pass it to the `params.parse` function. Since the help command and the help parameters are added on the fly.

```python
def help_modifier(help_param, help_command):
	# also do some modifications to help_param as well
	help_command.group = 'Other commands'

# params definition
parsed = params.parse(help_modifier=help_modifier)
```
