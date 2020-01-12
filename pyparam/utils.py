"""
Utililities for pyparam
"""
import re
import textwrap

class _Valuable:

    STR_METHODS = ('capitalize',
                   'center',
                   'count',
                   'decode',
                   'encode',
                   'endswith',
                   'expandtabs',
                   'find',
                   'format',
                   'index',
                   'isalnum',
                   'isalpha',
                   'isdigit',
                   'islower',
                   'isspace',
                   'istitle',
                   'isupper',
                   'join',
                   'ljust',
                   'lower',
                   'lstrip',
                   'partition',
                   'replace',
                   'rfind',
                   'rindex',
                   'rjust',
                   'rpartition',
                   'rsplit',
                   'rstrip',
                   'split',
                   'splitlines',
                   'startswith',
                   'strip',
                   'swapcase',
                   'title',
                   'translate',
                   'upper',
                   'zfill')

    def __str__(self):
        return str(self.value)

    def str(self):
        """Return the value in str type"""
        return str(self.value)

    def int(self, raise_exc=True):
        """Return the value in int type"""
        try:
            return int(self.value)
        except (ValueError, TypeError):
            if raise_exc:
                raise
            return None

    def float(self, raise_exc=True):
        """Return the value in float type"""
        try:
            return float(self.value)
        except (ValueError, TypeError):
            if raise_exc:
                raise
            return None

    def bool(self):
        """Return the value in bool type"""
        return bool(self.value)

    def __getattr__(self, item):
        # attach str methods
        if item in _Valuable.STR_METHODS:
            return getattr(str(self.value), item)
        raise AttributeError(
            'Class %r: No such attribute: %r' % (self.__class__.__name__, item)
        )

    def __add__(self, other):
        return self.value + other

    def __contains__(self, other):
        return other in self.value

    def __hash__(self): # pragma: no cover
        """
        Use id as identifier for hash
        """
        return id(self)

    def __eq__(self, other): # pragma: no cover
        return self.value == other

    def __ne__(self, other):
        return not self.__eq__(other)

class _Hashable:
    """
    A class for object that can be hashable
    """
    def __hash__(self):
        """
        Use id as identifier for hash
        """
        return id(self)

    def __eq__(self, other):
        """
        How to compare the hash keys
        """
        return id(self) == id(other)

    def __ne__(self, other):
        """
        Compare hash keys
        """
        return not self.__eq__(other)

def wraptext(text, width=70, **kwargs):
    """Wrap a text"""
    width -= 2 # for ending ' \'
    # keep the indentation
    # '  - hello world' =>
    # '  - hello \'
    # '    world'
    # '  1. hello world' =>
    # '  1. hello \'
    # '     world'
    match = re.match(r'\s*(?:[-*#]|\w{1,2}\.)?\s+', text)
    prefix = ' ' * len(match.group(0)) if match else ''

    kwargs['subsequent_indent'] = prefix + kwargs.get('subsequent_indent', '')
    wraps = textwrap.wrap(text, width, **kwargs)
    return [line + ' \\' if i < len(wraps) - 1 else line
            for i, line in enumerate(wraps)]
