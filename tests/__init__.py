import io
from functools import partial
import pytest
from rich.console import Console

def assert_rich_equal(rich1, rich2, cs):
    cs.print(rich1)
    x1 = cs.file.getvalue()
    cs.file.seek(0)
    cs.file.truncate(0)
    cs.print(rich2)
    x2 = cs.file.getvalue()
    cs.file.seek(0)
    cs.file.truncate(0)
    assert x1 == x2, f"\n{x1!r}\n!=\n{x2!r}"

@pytest.fixture
def console():
    ret = Console(
        file=io.StringIO(), color_system="truecolor"
    )

    ret.assert_rich_equal = partial(assert_rich_equal, cs=ret)

    return ret
