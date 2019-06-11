```python
from pyparam import commands
commands._prefix = '-'
# common options for all commands
commands._.workdir.desc      = 'The work directory.'
commands._.workdir.required  = 'The work directory.'
commands.show                = 'Shows information'
commands.show.all            = False
commands.show.all.desc       = 'Show all information'
commands.show.depth          = 2
commands.show.depth.desc     = 'Show the information on depth'
# alias
commands.list                = commands.show
commands.run                 = 'Run script'
commands.run.script.desc     = 'The script to run'
commands.run.script.required = True
print(commands._parse())
```
```shell
> python program.py
```
![subcommand][12]
```shell
> python program.py -workdir ./workdir show -depth 3 -all
('show', {'all': True, 'depth': 3}, {'workdir': './workdir'})
#command,command options,          common options
```