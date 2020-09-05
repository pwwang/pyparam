"""An example for pyparam"""
from rich import print # pylint: disable=redefined-builtin
from pyparam import Params
# program name, otherwise sys.argv[0]
params = Params(prog='pyparam', desc="An example for {prog}")
# adding parameters
params.add_param('i, int', type=int,
                 desc="An integer argument.")
params.add_param('float', default=0.1, # type float implied
                 desc="A float argument.")
params.add_param('str', type=str,
                 desc="A str argument.")
params.add_param('flag', type=bool,
                 desc="A flag argument.")
params.add_param('c,count', type='count',
                 desc="A count argument.")
params.add_param('a', type='auto', type_frozen=False,
                 desc="Value will be automatically casted.")
params.add_param('py', type='py',
                 desc="Value will be evaluated by `ast.literal_eval`.")
params.add_param('json', type='json',
                 desc="Value will be converted using `json.loads`.")
params.add_param('list', type='list',
                 desc="Values will be accumulated.")
params.add_param('path', type='path', required=True,
                 desc="Value will be casted into `pathlib.Path`.",
                 callback=( # check if path exists
                     lambda path: ValueError('File does not exist.')
                     if not path.exists() else path
                 ))
params.add_param('choice', type='choice', default='medium',
                 choices=['small', 'medium', 'large'],
                 desc="One of {choices}.")
params.add_param('config.ncores', default=1, # namespace config implied
                 argname_shorten=False,
                 desc='Number of cores to use.')

print(vars(params.parse()))
