import logging
import pytest

from pyparam.param import *
from pyparam.utils import logger

def test_paramauto():
    param = ParamAuto(
        ['a', 'arg'],
        default=1,
        desc=["Description"]
    )
    assert isinstance(param, Param)
    assert isinstance(param, ParamAuto)

    assert param._prefix_name('a') == '-a'
    assert param._prefix_name('arg') == '--arg'

    assert param.namespaces('len') == 0
    assert param.namespaces(0) == []

    assert not param.is_help
    param.is_help = True
    assert param.is_help
    assert param.optstr() == '-a, --arg'
    assert param.desc_with_default == ["Description"]

    param.is_help = False
    assert not param.is_help

    assert param.ns_param is None

    assert not param.is_positional

    assert param.name('short') == '-a'
    assert param.name('short', False) == 'a'
    assert param.name('long') == '--arg'
    assert param.name('long', False) == 'arg'

    assert param.namestr() == '-a, --arg'
    assert param.typestr() == 'auto'
    assert param.usagestr() == '--arg*AUTO'
    assert param.optstr() == '-a, --arg*<AUTO>'
    assert param.default_group == 'OPTIONAL OPTIONS'
    param.push(2)
    assert param._stack == [[2]]
    assert not param.hit

    assert repr(param).startswith('<ParamAuto(-a, --arg :: auto) @')
    assert param.value == 2

    paramint = param.to('int')
    assert paramint.type == 'int'

    assert paramint.consume('3')
    assert not paramint.consume('3')

def test_param_with_ns():
    ns = ParamNamespace(['c', 'config'])

    with pytest.raises(PyParamNameError):
        param = ParamInt(['c.a', 'arg'], default=1, desc=[''])

    param = ParamInt(['c.a', 'config.arg'], default=1, desc=['Description'])
    param.full_names()
    assert sorted(param.names) == ['c.a', 'c.arg', 'config.a', 'config.arg']

    param.ns_param = ns
    assert param.optstr() == '~<ns>.a, ~<ns>.arg*<INT>'
    assert param.default_group == 'OPTIONAL OPTIONS UNDER --config'


def test_custom_prefix():
    param = ParamInt('a, arg', default=1, desc=['Description'], prefix='--')
    assert param._prefix_name('a') == '--a'
    assert param._prefix_name('arg') == '--arg'

def test_close(caplog):
    caplog.set_level(logging.WARNING, logger=logger.name)
    param = ParamInt(['a', 'arg'], default=1, desc=['Description'])
    param2 = ParamList(['b'], default=[1], type=list, desc=['Description'])
    param.hit = True
    param.close()

    assert len(caplog.record_tuples) == 1
    assert caplog.record_tuples[0] == (
        logger.name, logging.WARNING,
        "No value provided for argument '-a, --arg'"
    )

    with pytest.raises(PyParamTypeError):
        param.overwrite_type('bool')

    with pytest.raises(PyParamTypeError):
        param2.overwrite_type('bool')

def test_push_warning(caplog):
    caplog.set_level(logging.INFO, logger=logger.name)
    param = ParamInt(['a'], default=1, desc='')
    param.push(1)
    assert len(caplog.record_tuples) == 0

    param.hit = True
    param.push('2')
    assert len(caplog.record_tuples) == 1
    assert caplog.record_tuples[0] == (
        logger.name, logging.WARNING,
        "Previous value of argument '-a' is overwritten with '2'."
    )

def test_required_not_consumed():
    param = ParamInt(['a'], default=1, desc='', required=True)
    with pytest.raises(PyParamValueError):
        param._value()

def test_subtype():
    param = ParamList(['a', 'arg'], default=None,
                      desc=['Description'], subtype='int')
    assert param.typestr() == 'list:int'

def test_desc_error():
    a = ParamInt('a', default=1, desc=['{xyz}'])
    with pytest.raises(PyParamException):
        a.desc

def test_desc_with_default():
    param = ParamList(['a'], default=[1], desc=['Description.'])
    assert param.desc_with_default == ['Description. Default: [1]']

    param = ParamList(['a'], default=[1], desc=['Description. Default: x'])
    assert param.desc_with_default == ['Description. Default: x']

def test_value_with_default():
    param = ParamFloat(['a'], default=0.1, desc=['Description'])
    assert param.value == 0.1
    # cached
    assert param.value == 0.1
    assert param.apply_callback(Namespace()) == 0.1

def test_callback():
    param = ParamInt(['a'], default=1, desc=['Description'],
                     callback=lambda x: x+1)
    assert param.apply_callback(Namespace()) == 2

    param = ParamInt(['a'], default=1, desc=['Description'],
                     callback=lambda x: ValueError(''))
    with pytest.raises(PyParamTypeError):
        param.apply_callback(Namespace())

    param = ParamInt(['a'], default=1, desc=['Description'],
                     callback=lambda x: x/0)
    with pytest.raises(PyParamTypeError):
        param.apply_callback(Namespace())

def test_paramstr():
    param = ParamStr(['a'], default=None, desc=['Description'])
    assert param.value == ''

def test_parambool():
    with pytest.raises(PyParamValueError):
        ParamBool(['a'], default='x', desc=['Description'])

    param = ParamBool(['a', 'arg'], default='false', desc=['Description'])
    assert param.usagestr() == '--arg'

    param.is_help = True
    assert param.optstr() == '-a, --arg'

    param.is_help = False
    assert param.optstr() == '-a, --arg*[BOOL]'

    ns = ParamNamespace(['ns'], default=None, type='ns', desc=['Description'])
    param.ns_param = ns

    assert param.optstr() == '~<ns>.a, ~<ns>.arg*[BOOL]'

    param.hit = True
    param.close()
    assert param.value

    param = ParamBool(['a', 'arg'], default='false', desc=['Description'])
    param.hit = True
    param.close()
    assert param.value

    param = ParamBool(['a', 'arg'], default='false', desc=['Description'])
    assert not param.consume('true')
    param.hit = True
    assert param.consume('true')
    assert not param.consume('true')
    assert param.value

    param.hit = True
    assert not param.consume('true1')

    param = ParamBool(['a', 'arg'], default='false', desc=['Description'])
    assert param._value() is False

def test_paramcount():
    param = ParamCount(['arg', 'a'], default=0, desc=['Description'])

    with pytest.raises(PyParamValueError):
        ParamCount(['a'], default=1, desc=['Description'])

    with pytest.raises(PyParamValueError):
        ParamCount(['arg'], default=0, desc=['Description'])

    with pytest.raises(PyParamValueError):
        ParamCount(['a'], default=0, desc=['Description'], max=-1)

    param.hit = True
    param.close()
    assert param.value == 1

    # copy
    param = param.to('count')
    param.hit = True
    param.close()
    assert param.value == 1

    param = param.to('count')
    assert not param.consume('1')
    param.hit = True
    assert param.consume('3')
    assert param.value == 3

    param.hit = True
    assert not param.consume('xx')

    param = param.to('count')
    param.push('aaa')
    assert param.value == 4

    param = param.to('count')
    param.push('ax')
    with pytest.raises(PyParamValueError):
        param.value

    param = param.to('count')
    param._kwargs['max'] = 2
    param.push('aaaa')
    with pytest.raises(PyParamValueError):
        param.value

def test_parampath():
    param = ParamPath(['a'], default='.', desc=['Description'])
    assert param.value == Path('.')

def test_parampy():
    param = ParamPy(['a'], default='[1]', desc=['Description'])
    assert param.value == [1]

def test_paramjson():
    param = ParamJson(['a'], default='[1]', desc=['Description'])
    assert param.value == [1]

def test_paramlist():
    param = ParamList(['a'], default=[1], desc=['Description'])

    assert param.consume(2)
    assert param.value == [1,2]

    param2 = param.overwrite_type('reset')
    assert param2 is param
    param.hit = True
    param.push(3)
    param._value_cached = None
    assert param.value == [3]

def test_paramchoice():
    param = ParamChoice(['a'], default=1, choices=[1,2,3], desc=['Description'])

    with pytest.raises(PyParamValueError):
        ParamChoice(['a'], default=1, desc=['Description'])

    with pytest.raises(PyParamValueError):
        ParamChoice(['a'], default=1, choices=1, desc=['Description'])

    assert param.value == 1

    param.push(4)
    param._value_cached = None
    with pytest.raises(PyParamValueError):
        param.value

    param = ParamChoice(['a'], default=None, choices=[3,2,1],
                        desc=['Description'])
    assert param.value == 3

def test_paramns():
    param = ParamNamespace(['c', 'config'], default=None, desc=['Description'])
    paramint = ParamInt(['c.a'], default=1, required=True, desc=['Description'])
    param.push(paramint)

    assert param.get_param('config.a') is paramint
    assert param.get_param('x.y') is None
    assert param.get_param('') is None

    assert param.default_group == 'REQUIRED OPTIONS'
    param.ns_param = param
    assert param.default_group == 'REQUIRED OPTIONS UNDER --config'

    param = param.to('ns')
    param.ns_param = None
    assert param.default_group == 'OPTIONAL OPTIONS'

    assert not param.consume('1')

    param = param.to('ns')
    param.ns_param = None
    paramint = ParamInt(
        ['c.a.b'], default=1, required=True, desc=['Description']
    )
    param.push(paramint)

    assert param.get_param('c.a.b') is paramint

    paramint = ParamInt(
        ['c.a.b', 'a.a.b'], default=1, required=True, desc=['Description']
    )
    with pytest.raises(PyParamValueError):
        param.push(paramint)

    param = param.to('ns')
    param.ns_param = None
    param_sub = ParamNamespace(
        ['c.n', 'config.ns'], default=None, desc=['Description'],
        callback=lambda value: value.a + 1
    )
    paramint = ParamInt(['c.ns.a'], default=1, desc=['Description'])
    param.push(param_sub)
    param.push(paramint)

    assert param.value.n.a == 1
    assert param.value.ns.a == 1

    assert param.apply_callback(Namespace()).n == 2

    param_sub.callback = lambda value: ValueError()
    with pytest.raises(PyParamTypeError):
        param.apply_callback(Namespace())

    param_sub.callback = lambda value: 1/0
    with pytest.raises(PyParamTypeError):
        param.apply_callback(Namespace())

def test_register_param():
    class ParamMy(Param):
        type = 'ns'

    with pytest.raises(PyParamNameError):
        register_param(ParamMy)
