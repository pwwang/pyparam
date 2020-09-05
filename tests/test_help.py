import pytest
from pyparam import Params
from pyparam.help import *

params = Params(
    prog='prog',
    desc = [
        'Program: {prog}',
        '>>> print(1)'
    ]
)
params.add_param('a', desc="""\
>>> print(2)

""")
params.add_param('b', default=2)
params.add_param('c', required=True)
params.add_param('d', desc="Newline in default. Default: 1\n2")
params.add_param('e', default=1, show=False, group='Grouped options')
params.add_command('cmd')

def test_helpassembler(capsys):
    ha = HelpAssembler('prog', 'default', None)
    assembled = ha.assemble(params)
    assert len(ha._assembled) % 3 == 0

    ha.printout()
    out = capsys.readouterr().out
    assert 'DESCRIPTION:' in out
    assert 'Program: prog' in out
    assert 'USAGE:' in out
    assert 'prog -c AUTO [OPTIONS]' in out
    assert 'OPTIONAL OPTIONS:' in out

def test_callback(capsys):
    def callback(assembled):
        assembled['NEW'] = ['123', '456']
    ha = HelpAssembler('prog', 'default', callback)
    params2 = Params()
    params2.desc = None
    ha.assemble(params2)
    ha.printout()

    out = capsys.readouterr().out
    assert 'NEW:' in out
