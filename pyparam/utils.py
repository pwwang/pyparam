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

def wraptext(text,
             width=70,
             defaults=("Default: ", "DEFAULT:"),
             break_long_words=False,
             **kwargs):
    """Wrap a text
    # keep the indentation
    # '  - hello world' =>
    # '  - hello \'
    # '    world'
    # '  1. hello world' =>
    # '  1. hello \'
    # '     world'
    """
    width -= 2 # for ending ' \'
    match = re.match(r'\s*(?:[-*#]|\w{1,2}\.)?\s+', text)
    prefix = ' ' * len(match.group(0)) if match else ''
    kwargs['subsequent_indent'] = prefix + \
                                  kwargs.get('initial_indent', '') + \
                                  kwargs.get('subsequent_indent', '')

    codes = re.findall(r'`[^`]+`', text)
    placeholders = {}
    for i, line in enumerate(codes):
        text = text.replace(line, '__code_%d__' % i)
        placeholders['__code_%d__' % i] = line

    if text.endswith(' \\'):
        return (kwargs.get('initial_indent', '') + text).splitlines()

    codes = textwrap.wrap(text,
                          width,
                          break_long_words=break_long_words,
                          **kwargs)

    if not codes:
        return codes

    default_index = None
    for i, line in enumerate(codes):
        for placeholder, origin in placeholders.items():
            line = line.replace(placeholder, origin)
        codes[i] = line
        if defaults and any(default in line for default in defaults):
            default_index = i

    # put default in a separate line
    if (default_index is not None and
            default_index < len(codes) - 1 and
            defaults and
            not any(codes[default_index].startswith(default)
                    for default in defaults)):
        line_default_index = [codes[default_index].rfind(default)
                              for default in defaults
                              if default in codes[default_index]][0]
        codes.insert(default_index+1, codes[default_index][line_default_index:])
        codes[default_index] = codes[default_index][:line_default_index]

    return [(line + ' \\')
            if i not in (len(codes)-1, default_index)
            else line
            for i, line in enumerate(codes)]
