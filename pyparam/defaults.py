"""Constants for pyparam"""

import colorama

# the max width of the help page, not including the leading space
MAX_PAGE_WIDTH = 100
# the max width of the option name
# (include the type and placeholder, but not the leading space)
MAX_OPT_WIDTH = 36
# the min gap between optname/opttype and option description
MIN_OPTDESC_LEADING = 5
# maximum warnings to print
MAX_WARNINGS = 10

THEMES = dict(
    default=dict(
        error=colorama.Fore.RED,
        warning=colorama.Fore.YELLOW,
        title=colorama.Style.BRIGHT + colorama.Fore.CYAN,  # section title
        prog=colorama.Style.BRIGHT + colorama.Fore.GREEN, # program name
        default=colorama.Fore.MAGENTA,              # default values
        optname=colorama.Style.BRIGHT + colorama.Fore.GREEN,
        opttype=colorama.Fore.BLUE,
        codebg=colorama.Back.BLACK,
        optdesc='',
    ),

    blue=dict(
        title=colorama.Style.BRIGHT + colorama.Fore.GREEN,
        prog=colorama.Style.BRIGHT + colorama.Fore.BLUE,
        optname=colorama.Style.BRIGHT + colorama.Fore.BLUE,
        opttype=colorama.Style.BRIGHT,
        codebg=colorama.Back.WHITE,
    ),

    plain=dict(
        error='',
        warning='',
        title='',
        prog='',
        default='',
        optname='',
        opttype=''
    )
)

OPT_ALLOWED_TYPES = ('str',
                     'int',
                     'float',
                     'bool',
                     'list',
                     'py',
                     'NoneType',
                     'dict')

OPT_TYPE_MAPPINGS = dict(a='auto',
                         auto='auto',
                         i='int',
                         int='int',
                         n='NoneType',
                         f='float',
                         float='float',
                         b='bool',
                         bool='bool',
                         none='NoneType',
                         s='str',
                         str='str',
                         d='dict',
                         dict='dict',
                         box='dict',
                         p='py',
                         py='py',
                         python='py',
                         r='reset',
                         reset='reset',
                         l='list',
                         list='list',
                         array='list',
                         v='verbose',
                         verb='verbose',
                         verbose='verbose')

OPT_BOOL_TRUES = [True, 1, 'True', 'TRUE', 'true', '1']

OPT_BOOL_FALSES = [False,
                   0,
                   'False',
                   'FALSE',
                   'false',
                   '0',
                   'None',
                   'none',
                   None]

OPT_NONES = [None, 'none', 'None']

OPT_PATTERN = r"^([a-zA-Z@][\w,\._-]*)?(?::([\w:]+))?(?:=(.*))?$"
OPT_INT_PATTERN = r'^[+-]?\d+$'
OPT_FLOAT_PATTERN = r'^[+-]?(?:\d*\.)?\d+(?:[Ee][+-]\d+)?$'
OPT_NONE_PATTERN = r'^none|None$'
OPT_BOOL_PATTERN = r'^(%s)$' % ('|'.join(
    set(str(x) for x in OPT_BOOL_TRUES + OPT_BOOL_FALSES)
))
OPT_PY_PATTERN = r'^(?:py|repr):(.+)$'

OPT_POSITIONAL_NAME = '_'
OPT_UNSET_VALUE = '__Param_Value_Not_Set__'
CMD_GLOBAL_OPTPROXY = '_'

REQUIRED_OPT_TITLE = 'REQUIRED OPTIONS'
OPTIONAL_OPT_TITLE = 'OPTIONAL OPTIONS'
DEFAULTS = ['Default: ', 'DEFAULT: ']
