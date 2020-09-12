import logging
from pathlib import Path
import pytest
from pyparam.params import *
from pyparam.exceptions import PyParamTypeError

params = Params()
def setup_function():
    params.params = OrderedDiot()
    params.commands = OrderedDiot()
    params.prefix = 'auto'
    params.prog = 'pyparam'
    params.arbitrary = False
    params.help_on_void = True

def test_init():
    assert isinstance(params, Params)

def test_more():
    p = Params('c, cmd')
    assert p.names == ['c', 'cmd']
    assert p.name() == 'c'
    assert p.name('long') == 'cmd'
    assert p.namestr() == 'c, cmd'

    p.add_param('a.b.c', callback=lambda x: str(x))

    with pytest.raises(PyParamTypeError):
        p.add_param('a', type='xyz')

    with pytest.raises(PyParamNameError):
        p.add_param('a')

    with pytest.raises(PyParamNameError):
        p.add_command('a')

    p.add_command('cmd')

    values = p.values()
    assert len(values) == 1
    assert values.a.b.c == 'None'
    with pytest.raises(SystemExit):
        p.print_help()

def test_parse():
    with pytest.raises(SystemExit):
        params.parse([])

    sys.argv = [sys.argv[0]]
    with pytest.raises(SystemExit):
        params.parse()

    params.add_param('a.b.c', default=1)
    params.add_param('v', type='count')
    parsed = params.parse(['-a.b.c', '2'])
    assert parsed.a.b.c == 2
    assert parsed.v == 0

    assert params.get_param('v') is params.params.v
    assert params.get_param('a.b.c.d') is None

    del params.params.a
    assert params.get_param('a.b.c') is None

    cmd = params.add_command('cmd')
    assert params.get_command('cmd') is cmd

def test_parse_wrong_value():
    params.add_param('i, int', type='int')

    with pytest.raises(SystemExit):
        params.parse(['-i', '1.1'])

    parsed = params.parse(['-i', '1'])
    assert parsed.i == 1

def test_parse_callback_error():
    params.add_param('f', type='float', callback=lambda x: 1/0)

    with pytest.raises(SystemExit):
        params.parse(['-f', '1'])

def test_parse_command():
    cmd = params.add_command('cmd')
    cmd.add_param('x', default=False)

    parsed = params.parse(['cmd', '-x'])
    assert parsed.cmd.x is True

    with pytest.raises(SystemExit):
        params.parse(['cmd2'])

    with pytest.raises(SystemExit):
        params.parse(['help', 'cmd'])

    with pytest.raises(SystemExit):
        params.parse(['help', 'cmd2'])

    with pytest.raises(SystemExit):
        params.parse(['help', ''])

    with pytest.raises(SystemExit):
        params.parse(['help', '-h'])

    cmd.help_on_void = False
    cmd.add_param('x', default=False, force=True)
    parsed = params.parse(['cmd'])
    assert parsed.cmd.x is False

    cmd.add_param('x', default=False, force=True)
    cmd.add_param('i', default=0)
    parsed = params.parse(['cmd', '-x', '-i', '1'])
    assert parsed.cmd.x is True
    assert parsed.cmd.i == 1

def test_parse_type_overwrite():
    cmd = params.add_command('cmd')
    cmd.add_param('x', default=False)
    cmd.add_param('i', default=0, type_frozen=False)
    parsed = params.parse(['cmd', '-x', '-i:float', '1.1'])
    assert parsed.cmd.x is True
    assert parsed.cmd.i == 1.1

def test_parse_type_overwrite_ns():
    params.add_param('a.b', type=int, type_frozen=False)
    parsed = params.parse(['-a.b:float', '1.1'])
    assert parsed.a.b == 1.1

def test_parse_unknown_values(caplog):
    cmd = params.add_command('cmd')
    cmd.add_param('x', default=False)
    caplog.clear()
    caplog.set_level(logging.INFO, logger=logger.name)
    params.parse(['cmd', '-x', '-f', '1.1'])
    assert len(caplog.record_tuples) == 2
    assert caplog.record_tuples[0] == (
        logger.name, logging.WARNING, "Unknown argument: '-f', skipped"
    )
    assert caplog.record_tuples[1] == (
        logger.name, logging.WARNING, "Unknown value: '1.1', skipped"
    )

    params.add_param('c', type='count')
    cmd.add_param('x', default=False, force=True)
    cmd.add_param('i', default=0, force=True, type_frozen=False)
    cmd.add_param(POSITIONAL, type='auto')
    parsed = params.parse(['-ccc', 'cmd', '-x', '-i', '2', '3', '4'])
    assert parsed.c == 3
    assert parsed.cmd.x is True
    assert parsed.cmd.i == 2
    assert parsed.cmd[POSITIONAL] == 3

def test_positional():
    params.add_param(POSITIONAL)
    parsed = params.parse(['1', '2', '3'])
    assert parsed[POSITIONAL] == [1,2,3]

def test_non_default_prefix():
    params.prefix = '+'

    params.add_param(POSITIONAL)
    params.add_param('i')
    parsed = params.parse(['+i1', '2', '+x', '3'])
    assert parsed.i == 1

def test_unregconized_value():
    params.add_param(POSITIONAL)
    params.add_param('i')
    parsed = params.parse(['-i1', '2', '-x', '3'])
    assert parsed.i == 1

def test_arbitrary():
    params.arbitrary = True
    parsed = params.parse(['1', '2', '3'])
    assert parsed[POSITIONAL] == [1,2,3]

def test_arbitrary_cmd():
    params.arbitrary = True
    parsed = params.parse(['cmd', '-x', '1'])
    assert parsed.cmd.x == 1

def test_from_file_full():
    here = Path(__file__).parent
    params.from_file(here/'full.toml')
    params.help_on_void = False
    parsed = params.parse(['cmd'])
    assert parsed['int'] == 1
    assert parsed.cmd['float'] == 0.1

def test_from_file_express():
    here = Path(__file__).parent
    params.from_file(here/'express.toml')
    params.help_on_void = False
    parsed = params.parse(['cmd'])
    assert parsed['int'] == 1
    assert parsed['float'] == 0.1

def test_from_arg_names():
    here = Path(__file__).parent
    params.help_on_void = False
    args = ['--file', str(here/'full.toml'), 'cmd']
    params.from_arg('file', args=args)
    parsed = params.parse(args)
    assert parsed['int'] == 1
    assert parsed.cmd['float'] == 0.1

def test_from_arg_param():
    here = Path(__file__).parent
    params.help_on_void = False
    param = params.add_param('file')
    args = ['--file', str(here/'full.toml'), 'cmd']
    params.from_arg(param, args=args)
    parsed = params.parse(args)
    assert parsed['int'] == 1
    assert parsed.cmd['float'] == 0.1

def test_param_reuse():
    cmd1 = params.add_command('cmd1', help_on_void=False)
    cmd2 = params.add_command('cmd2', help_on_void=False)
    cmd3 = params.add_command('cmd3', help_on_void=False)
    param1 = cmd1.add_param('i', default=1)
    param2 = cmd1.add_param('l', default=[1,2])
    param3 = cmd1.add_param('c', type='ns')
    param4 = cmd1.add_param('c.a', default=[8,9])
    cmd2.add_param(param1)
    cmd2.add_param(param2)
    cmd2.add_param(param3)
    cmd3.add_param(param4)

    parsed1 = params.parse(["cmd1"])
    assert parsed1.cmd1.i == 1
    assert parsed1.cmd1.l == [1, 2]
    assert parsed1.cmd1.c.a == [8, 9]

    parsed2 = params.parse(["cmd2", "-i2", "-l3", "-c.a", "0"])
    assert parsed2.cmd2.i == 2
    assert parsed2.cmd2.l == [1, 2, 3]
    assert parsed2.cmd2.c.a == [8, 9, 0]
    # orginal doesn't change
    assert parsed1.cmd1.i == 1
    assert parsed1.cmd1.l == [1, 2]
    assert parsed1.cmd1.c.a == [8, 9]

    parsed3 = params.parse(["cmd3", "-c.a", "5"])
    assert parsed3.cmd3.c.a == [8, 9, 5]

    # orginal doesn't change
    assert parsed1.cmd1.i == 1
    assert parsed1.cmd1.l == [1, 2]
    assert parsed1.cmd1.c.a == [8, 9]

def test_help_modifier():
    def help_modifier(help_param, help_cmd):
        help_param.group = 'Other arguments'
    params.help_modifier = help_modifier

    with pytest.raises(SystemExit):
        params.parse()

    assert params.get_param('h').group == 'Other arguments'

def test_to_dict():
    d = params.to_dict()
    assert len(d['params']) == 0
    assert len(d['commands']) == 0

    param1 = params.add_param('i, int',
                              default=1,
                              type=int,
                              desc='Int parameter',
                              show=False,
                              required=True,
                              type_frozen=False,
                              argname_shorten=False)
    d = params.to_dict()
    assert len(d['params']) == 1

    params2 = Params()
    params2.from_dict(d)
    param2 = params2.get_param('i')

    assert d.params['i'].group == 'REQUIRED OPTIONS'
    assert param1.names == param2.names
    assert param1.default == param2.default
    assert param1.type == param2.type
    assert param1.desc == param2.desc
    assert param1.show == param2.show
    assert param1.required == param2.required
    assert param1.type_frozen == param2.type_frozen
    assert param1.argname_shorten == param2.argname_shorten

    cmd = params.add_command(
        'cmd, cmd1',
        help_keys='H',
        help_cmds='hlp',
        desc='subcommand',
        help_on_void=False,
        prefix='+',
        arbitrary=True,
        theme='synthware',
        usage='{prog} [options]',
        group='X Commands'
    )
    cmd.add_param('j')
    d = params.to_dict()
    assert d.commands.cmd.params == cmd.to_dict().params
    assert d.commands.cmd.commands == cmd.to_dict().commands

    assert d.commands.cmd.desc == cmd.desc
    assert d.commands.cmd.help_keys == d.commands.cmd.help_keys
    assert d.commands.cmd.help_cmds == d.commands.cmd.help_cmds
    assert d.commands.cmd.help_on_void == d.commands.cmd.help_on_void
    assert d.commands.cmd.prefix == d.commands.cmd.prefix
    assert d.commands.cmd.arbitrary == d.commands.cmd.arbitrary
    assert d.commands.cmd.theme == d.commands.cmd.theme
    assert d.commands.cmd.usage == d.commands.cmd.usage
    assert d.commands.cmd.group == 'X Commands'

@pytest.mark.parametrize("cfgtype", [
    "params.toml", "params.json", "params.yaml"
])
def test_to_file(tmp_path, cfgtype):
    path = tmp_path / cfgtype
    param1 = params.add_param('i, int')
    params.add_command('cmd, cmd1').add_param('j')
    params.to_file(str(path))

    params2 = Params()
    params2.from_file(path)
    param2 = params2.get_param('i')
    assert param1.names == param2.names
    assert param1.default == param2.default
    assert param1.type == param2.type
    assert param1.desc == param2.desc
    assert param1.show == param2.show
    assert param1.required == param2.required
    assert param1.type_frozen == param2.type_frozen
    assert param1.argname_shorten == param2.argname_shorten

    assert params2.commands.cmd.desc == params.commands.cmd.desc
    assert params2.commands.cmd.help_keys == params.commands.cmd.help_keys
    assert params2.commands.cmd.help_cmds == params.commands.cmd.help_cmds
    assert params2.commands.cmd.help_on_void == params.commands.cmd.help_on_void
    assert params2.commands.cmd.prefix == params.commands.cmd.prefix
    assert params2.commands.cmd.arbitrary == params.commands.cmd.arbitrary
    assert params2.commands.cmd.theme == params.commands.cmd.theme
    assert params2.commands.cmd.usage == params.commands.cmd.usage

def test_to_file_error():
    with pytest.raises(ValueError):
        params.to_file('abc.def')

def test_command_reuse():
    params2 = Params('cmd,cmd1')
    params.add_command(params2)
    assert params.commands.cmd is params.commands.cmd1
    assert params2.prog == 'pyparam cmd1'
    assert repr(params2).startswith('<Params(cmd,cmd1) @ ')

def test_copy():
    params.add_param('i', default=0)
    # shallow
    params_copied = params.copy()
    parsed = params.parse(['-i', '1'])
    assert parsed.i == 1
    assert params_copied.values().i == 1

def test_deepcopy():
    params1 = Params()
    params1.add_command('cmd,cmd1').add_param('i,int', default=1)

    params2 = params1.copy(deep=True)
    params2.commands.cmd.add_param('j', default=2)

    parsed = params1.parse(['cmd', '-i', '3', '-j', '8'])
    assert parsed.cmd.i == 3
    assert 'j' not in parsed.cmd

    values = params2.commands.cmd.values()
    assert values.i == 1
    assert values.j == 2

