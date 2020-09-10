import os
import pytest
from pyparam import Params
from pyparam.completer import *

params = Params(prog='pyparam')
params.add_param('i', default=1, desc='Int parameter')
params.add_param('c', type='count', desc='Count parameter')
params.add_param('cfg.os', type='choice', required=True,
                    choices=["win", "windows", "osx"],
                    desc='Choice parameter')
cmd = params.add_command('cmd', desc='A subcommand')
cmd.add_param(
    'x', type='choice', choices=['11', '12', '23'],
    desc='Choice parameter with complete callback',
    complete_callback=lambda current, prefix: [
        (f'{prefix}11', 'First value'),
        (f'{prefix}12', 'Second value'),
        (f'{prefix}23', 'Third value'),
    ]
)
cmd.add_param(
    'b', type='bool', desc='Bool parameter',
    complete_callback=lambda current, prefix: [
        (f'{prefix}TRUE', 'True'),
        (f'{prefix}True', 'True'),
    ]
)
cmd2 = params.add_command('cmd2', desc='Cmd2')
cmd2.add_param('b2', default=False, desc='Bool parameter')
cmd3 = params.add_command('cmd3', desc='Cmd3')
cmd3.add_param('count,c', type='count', desc='Count parameter', max=3)
cmd4 = params.add_command('cmd4', desc='Cmd4')
cmd4.add_param('path', type='path', desc='Path parameter',
               complete_callback=lambda current, prefix:
               [(f'{prefix}abc', 'ABC')])
cmd4.add_param('dir', type='dir', desc='Dir parameter',
               complete_callback=lambda current, prefix:
               [(f'{prefix}def', 'DEF')])
cmd4.add_param('path2', type='path', desc='Path2 parameter')
cmd4.add_param('dir2', type='dir', desc='Dir2 parameter')
cmd4.add_param('config.subcfg.os', type='choice',
               choices=['win', 'windows', 'osx'],
               desc='OS parameter')


def _set_env(shell, words, cword):
    os.environ[f'{params.progvar}_COMPLETE_SHELL_{params.uid}'.upper()] = shell
    os.environ['COMP_WORDS'] = words
    os.environ['COMP_CWORD'] = str(cword)
    try:
        Completer.__init__(params)
    except SystemExit:
        pass

@pytest.mark.parametrize("string,expected", [
    ("a b c", ["a", "b", "c"]),
    ("'a d' b c", ["a d", "b", "c"])
])
def test_split_arg_string(string, expected):
    assert split_arg_string(string) == expected

@pytest.mark.parametrize("shell,python,module,expected", [
    ('bash', None, False, COMPLETION_SCRIPT_BASH % dict(
        complete_script='$1',
        script_name='pyparam',
        complete_func=f"_pyparam_completion_{params.uid}",
        complete_shell_var=f"pyparam_COMPLETE_SHELL_{params.uid}".upper(),
    )),
    ('fish', None, False, COMPLETION_SCRIPT_FISH % dict(
        complete_script='$COMP_WORDS[1]',
        script_name='pyparam',
        complete_func=f"__fish_pyparam_{params.uid}",
        complete_shell_var=f"pyparam_COMPLETE_SHELL_{params.uid}".upper(),
    )),
    ('zsh', None, False, COMPLETION_SCRIPT_ZSH % dict(
        complete_script='$words[1]',
        script_name='pyparam',
        complete_func=f"_pyparam_completion_{params.uid}",
        complete_shell_var=f"pyparam_COMPLETE_SHELL_{params.uid}".upper(),
    )),
])
def test_shellcode(shell, python, module, expected):
    assert params.shellcode(shell, python, module).rstrip() == expected.rstrip()

def test_shellcode_error():
    with pytest.raises(ValueError):
        params.shellcode('abc')

def test_complete_void(capsys):


    _set_env('fish', 'pyparam', -1)
    with pytest.raises(SystemExit):
        params.parse()

    assert sorted(capsys.readouterr().out.splitlines()) == sorted([
        "-i\tplain\tInt parameter",
        "-c\tplain\tCount parameter",
        "--cfg.os\tplain\tChoice parameter",
        "-h\tplain\tPrint help information for this command",
        "--help\tplain\tPrint help information for this command",
    ])

    _set_env('fish', 'pyparam', 2)
    with pytest.raises(SystemExit):
        params.parse()

    assert sorted(capsys.readouterr().out.splitlines()) == sorted([
        "-i\tplain\tInt parameter",
        "-c\tplain\tCount parameter",
        "--cfg.os\tplain\tChoice parameter",
        "-h\tplain\tPrint help information for this command",
        "--help\tplain\tPrint help information for this command",
    ])

    _set_env('bash', 'pyparam', 2)
    with pytest.raises(SystemExit):
        params.parse()

    assert sorted(capsys.readouterr().out.splitlines()) == sorted([
        "-i\tplain",
        "-c\tplain",
        "-h\tplain",
        "--cfg.os\tplain",
        "--help\tplain",
    ])

    _set_env('zsh', 'pyparam', 2)
    with pytest.raises(SystemExit):
        params.parse()

    assert sorted(capsys.readouterr().out.splitlines()) == sorted([
        "-i",
        "plain",
        "Int parameter",
        "-c",
        "plain",
        "Count parameter",
        "--cfg.os",
        "plain",
        "Choice parameter",
        "-h",
        "plain",
        "Print help information for this command",
        "--help",
        "plain",
        "Print help information for this command",
    ])


def test_complete_withcmd(capsys):
    _set_env('fish', 'pyparam --cfg.os win', -1)
    with pytest.raises(SystemExit):
        params.parse()

    assert sorted(capsys.readouterr().out.splitlines()) == sorted([
        "-i\tplain\tInt parameter",
        "-c\tplain\tCount parameter",
        "-h\tplain\tPrint help information for this command",
        "--help\tplain\tPrint help information for this command",
        "cmd\tplain\tCommand: A subcommand",
        "cmd2\tplain\tCommand: Cmd2",
        "cmd3\tplain\tCommand: Cmd3",
        "cmd4\tplain\tCommand: Cmd4",
        "help\tplain\tCommand: Print help of sub-commands"
    ])

def test_complete_cmd_void(capsys):
    _set_env('fish', 'pyparam --cfg.os win cmd', -1)
    with pytest.raises(SystemExit):
        params.parse()
    assert sorted(capsys.readouterr().out.splitlines()) == sorted([
        "-x\tplain\tChoice parameter with complete callback",
        "-b\tplain\tBool parameter",
        "-h\tplain\tPrint help information for this command",
        "--help\tplain\tPrint help information for this command",
    ])


def test_complete_prefix_callback(capsys):
    _set_env('fish', 'pyparam --cfg.os win cmd -x=', 4)
    with pytest.raises(SystemExit):
        params.parse()
    assert sorted(capsys.readouterr().out.splitlines()) == sorted([
        "-x=11\tplain\tFirst value",
        "-x=12\tplain\tSecond value",
        '-x=23\tplain\tThird value',
    ])

def test_complete_bool_callback(capsys):
    _set_env('fish', 'pyparam --cfg.os win cmd -b', 5)
    with pytest.raises(SystemExit):
        params.parse()
    assert sorted(capsys.readouterr().out.splitlines()) == sorted([
        "True\tplain\tTrue",
        "TRUE\tplain\tTrue",
    ])

    _set_env('fish', 'pyparam --cfg.os win cmd2 --b2 t', 5)
    with pytest.raises(SystemExit):
        params.parse()
    assert sorted(capsys.readouterr().out.splitlines()) == sorted([
        "true\tplain\tValue True",
    ])

    _set_env('fish', 'pyparam --cfg.os win cmd2 --b2 f', 5)
    with pytest.raises(SystemExit):
        params.parse()
    assert sorted(capsys.readouterr().out.splitlines()) == sorted([
        "false\tplain\tValue False",
    ])

    _set_env('fish', 'pyparam --cfg.os win cmd2 --b2', 5)
    with pytest.raises(SystemExit):
        params.parse()
    assert sorted(capsys.readouterr().out.splitlines()) == sorted([
        "-h\tplain\tPrint help information for this command",
        "--help\tplain\tPrint help information for this command"
    ])

    params.comp_shell = ''
    _set_env('bash', 'python', 2)
    assert params.comp_shell == ''

def test_complete_count_name(capsys):
    _set_env('fish', 'pyparam --cfg.os win cmd3 -c', 4)
    with pytest.raises(SystemExit):
        params.parse()
    assert sorted(capsys.readouterr().out.splitlines()) == sorted([
        "-cc\tplain\tCount parameter",
        "-ccc\tplain\tCount parameter"
    ])

    _set_env('fish', 'pyparam --cfg.os win cmd3 -ccc', 4)
    with pytest.raises(SystemExit):
        params.parse()
    assert capsys.readouterr().out.strip() == ''

    _set_env('fish', 'pyparam -h=t', 1)
    with pytest.raises(SystemExit):
        params.parse()
    assert capsys.readouterr().out.strip() == ''

def test_complete_path_dir(capsys):

    _set_env('fish', 'pyparam --cfg.os win cmd4 --path', 5)
    with pytest.raises(SystemExit):
        params.parse()
    assert sorted(capsys.readouterr().out.splitlines()) == sorted([
        "abc\tplain\tABC",
    ])
    _set_env('fish', 'pyparam --cfg.os win cmd4 --dir', 5)
    with pytest.raises(SystemExit):
        params.parse()
    assert sorted(capsys.readouterr().out.splitlines()) == sorted([
        "def\tplain\tDEF",
    ])

    _set_env('fish', 'pyparam --cfg.os win cmd4 --path2', 5)
    with pytest.raises(SystemExit):
        params.parse()
    assert sorted(capsys.readouterr().out.splitlines()) == sorted([
        "\tfile\t"
    ])
    _set_env('fish', 'pyparam --cfg.os win cmd4 --dir2', 5)
    with pytest.raises(SystemExit):
        params.parse()
    assert sorted(capsys.readouterr().out.splitlines()) == sorted([
        "\tdir\t"
    ])

def test_complete_nest_ns(capsys):
    _set_env('fish', 'pyparam --cfg.os win cmd4 --config', 4)
    with pytest.raises(SystemExit):
        params.parse()
    assert sorted(capsys.readouterr().out.splitlines()) == sorted([
        "--config.subcfg.os\tplain\tOS parameter"
    ])
    _set_env('fish', 'pyparam --cfg.os win cmd4 --config.subcfg.os=w', 4)
    with pytest.raises(SystemExit):
        params.parse()
    assert sorted(capsys.readouterr().out.splitlines()) == sorted([
        "--config.subcfg.os=win\tplain\t",
        "--config.subcfg.os=windows\tplain\t"
    ])


def test_complete_prepare(capsys):
    params.comp_shell = ''
    _set_env('bash', 'python abc', 2)
    assert params.comp_shell == ''

    _set_env('bash', 'python -m', 2)
    assert params.comp_shell == ''

    _set_env('bash', 'python -m abc', 2)
    assert params.comp_shell == ''

    _set_env('bash', 'pyparam 1 2', 2)
    assert params.comp_shell == 'bash'
    assert params.comp_words == ['1']
    assert params.comp_curr == '2'
    assert params.comp_prev == '1'

    _set_env('bash', 'pyparam 1 2 =', 3)
    assert params.comp_shell == 'bash'
    assert params.comp_words == ['1', '2']
    assert params.comp_curr == ''
    assert params.comp_prev == '2'

    _set_env('bash', 'pyparam 1 2 = a', 4)
    assert params.comp_shell == 'bash'
    assert params.comp_words == ['1', '2']
    assert params.comp_curr == 'a'
    assert params.comp_prev == '2'

    _set_env('zsh', 'pyparam -i', 2)
    with pytest.raises(SystemExit):
        params.parse()

    assert capsys.readouterr().out.strip() == ''
