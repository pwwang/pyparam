
import pytest
from pyparam.utils import *
from rich.padding import Padding
from rich.syntax import Syntax
from . import console

def test_namespace():
    ns = Namespace()
    assert len(ns) == 0
    assert not bool(ns)
    assert 'a' not in ns

    ns['a'] = 1
    assert ns['a'] == 1
    assert len(ns) == 1
    assert bool(ns)
    assert ns
    assert 'a' in ns

class TestCodeblock:

    def test_init(self):
        cb = Codeblock('>>>', 'pycon', 0)
        assert isinstance(cb, Codeblock)
        assert cb.opentag == '>>>'
        assert cb.lang == 'pycon'

        assert repr(cb) == '<Codeblock (tag=>>>, lang=pycon, codes=[] ...)'

    @pytest.mark.parametrize("cb,end,out", (
        [Codeblock('>>>', 'pycon', 0), "", True],
        [Codeblock('>>>', 'pycon', 0), ">>>", False],
        [Codeblock('```', 'pycon', 0), "```", True],
        [Codeblock('```', 'pycon', 0), "````", False],
        [Codeblock('````', 'pycon', 0), "```", False],
        [Codeblock('````', 'pycon', 0), "````", True],
    ))
    def test_is_end(self, cb, end, out):
        assert cb.is_end(end) is out

    def test_render(self, console):
        cb = Codeblock('>>>', 'pycon', 1)
        cb.add_code(' >>> print("Hello world!")')
        console.assert_rich_equal(cb.render(), Padding(
            Syntax('>>> print("Hello world!")\n', 'pycon'),
            (0,0,0,1)
        ))

    def test_scan_plain(self):
        scanned, cb = Codeblock.scan("a\nb\nc")
        assert scanned == ['a', 'b', 'c']
        assert cb is None

    def test_scan_default(self):
        scanned, cb = Codeblock.scan("a\nb. Default: 1", check_default=True)
        assert scanned == ['a', 'b. Default: 1']
        assert cb is None

    def test_scan_pycon(self):
        scanned, cb = Codeblock.scan(
            "Not a codeblock\n"
            ">>> print(1)\n"
            "Default: 1",
            check_default=True
        )
        assert len(scanned) == 3
        assert scanned[0] == 'Not a codeblock'
        assert isinstance(scanned[1], Codeblock)
        assert scanned[2] == 'Default: 1'
        assert cb is None

    def test_scan_pycon_ended(self):
        scanned, cb = Codeblock.scan(
            "Not a codeblock\n"
            ">>> print(1)\n"
            "end.\n" # end of codeblock
            "Default: 1",
            check_default=True
        )
        assert len(scanned) == 4
        assert scanned[0] == 'Not a codeblock'
        assert isinstance(scanned[1], Codeblock)
        assert scanned[2] == 'end.'
        assert scanned[3] == 'Default: 1'
        assert cb is None

    def test_scan_pycon_open(self):
        scanned, cb = Codeblock.scan(
            "Not a codeblock\n"
            ">>> print(1)",
            check_default=True
        )
        assert len(scanned) == 2
        assert scanned[0] == 'Not a codeblock'
        assert isinstance(scanned[1], Codeblock)
        assert isinstance(cb, Codeblock)

    def test_scan_backticks(self):
        scanned, cb = Codeblock.scan(
            "Not a codeblock\n"
            "```python\n"
            "print(1)\n"
            "```\n"
            "Default: 1",
            check_default=True
        )
        assert len(scanned) == 3
        assert scanned[0] == 'Not a codeblock'
        assert isinstance(scanned[1], Codeblock)
        assert scanned[2] == 'Default: 1'
        assert cb is None

    def test_scan_backticks_open(self):
        scanned, cb = Codeblock.scan(
            "Not a codeblock\n"
            "```python\n"
            "print(1)\n",
            check_default=True
        )
        assert len(scanned) == 2
        assert scanned[0] == 'Not a codeblock'
        assert isinstance(scanned[1], Codeblock)
        assert isinstance(cb, Codeblock)

    def test_scan_texts(self):
        scanned = Codeblock.scan_texts([
            "Not a codeblock",
            ">>> print(1)",
            ">>> print(2)",
            "End of codeblock1.",
            "",
            "```python",
            "print(1)",
            "```",
            "End of codeblock2.",
        ])
        assert len(scanned) == 6
        assert scanned[0] == 'Not a codeblock'
        assert isinstance(scanned[1], Codeblock)
        assert scanned[2] == 'End of codeblock1.'
        assert scanned[3] == ''
        assert isinstance(scanned[4], Codeblock)
        assert scanned[5] == 'End of codeblock2.'

@pytest.mark.parametrize("str_or_list,strip,split,expected", [
    ((1,2,3), True, False, [1,2,3]),
    ([1,2,3], True, False, [1,2,3]),
    ("1, 2, 3", True, ",", ["1","2","3"]),
    ("1, 2, 3", True, False, ["1, 2, 3"]),
])
def test_always_list(str_or_list, strip, split, expected):
    assert always_list(str_or_list, strip, split) == expected

@pytest.mark.parametrize("typestr,expected", [
    (None, [None, None]),
    ('i:s', ['int', 'str']),
    ('i', ['int', None])
])
def test_parse_type(typestr, expected):
    assert parse_type(typestr) == expected

def test_parse_type_error():
    with pytest.raises(PyParamTypeError):
        parse_type('not a type')

@pytest.mark.parametrize("arg,prefix,allow_attached,expected", [
    ('a', '-', False, (None, None, 'a')),
    ('a', '+', False, (None, None, 'a')),
    ('+a', '+', False, ('a', None, None)),
    ('-a', 'auto', False, ('a', None, None)),
    ('-a:int=1', 'auto', False, ('a', 'int', '1')),
    ('--arg', 'auto', False, ('arg', None, None)),
    ('-a.bc', 'auto', False, ('a.bc', None, None)),
    ('-a1', 'auto', True, ('a', None, '1')),
    ('--a', 'auto', False, (None, None, '--a')),
    ('+a1', '+', True, ('a', None, '1')),
    ('+a1', '+', False, ('a1', None, None)),
])
def test_parse_positional_argument(arg, prefix, allow_attached, expected):
    assert parse_potential_argument(arg, prefix, allow_attached) == expected

@pytest.mark.parametrize("value,expected", [
    (1, 'int'),
    (1.1, 'float'),
    ("a", 'str'),
    (True, 'bool'),
    ([], 'list'),
    ([1,2,3], 'list:int'),
    ([1,2,'a'], 'list'),
    ({'a': 1}, 'json'),
    (Path('.'), 'path'),
    (None, 'auto'),
])
def test_type_from_value(value, expected):
    assert type_from_value(value) == expected

def test_type_from_value_error():
    with pytest.raises(PyParamTypeError):
        type_from_value([[1]])

@pytest.mark.parametrize("value,to_type,expected", [
    ('1', 'int', 1),
    ('1.1e-1', 'float', 0.11),
    (1, 'str', '1'),
    ('true', 'bool', True),
    ('false', 'bool', False),
    ('.', 'path', Path('.')),
    ('{1,2,3}', 'py', {1,2,3}),
    ('[1,2,3]', 'json', [1,2,3]),
    ('1', 'auto', 1),
    ('true', 'auto', True),
    ('false', 'auto', False),
    ('1.1', 'auto', 1.1),
    ('[1,2,3]', 'auto', [1,2,3]),
    ('abcd', 'auto', 'abcd'),
])
def test_cast_to(value, to_type, expected):
    assert cast_to(value, to_type) == expected

def test_cast_to_error():
    with pytest.raises(PyParamTypeError):
        cast_to('a', 'bool')
    with pytest.raises(PyParamTypeError):
        cast_to('a', 'ns')
