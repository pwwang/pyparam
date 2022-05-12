## 0.5.2

- 🩹 Fix newline lost of section title in help (Textualize/rich#2274)

## 0.5.1

- 📄 Add license

## 0.5.0

- ⬆️ Upgrade python-simpleconf to v0.5
- 👷 Remove python3.6 and add python3.10 in CI

## 0.4.17

- 👽️ Adopt rich 11+

## 0.4.16

- 🩹 Fix description formatting exception not captured

## 0.4.15

- 🐛 Allow namespace parameter to be defined in express way from a file

## 0.4.14

- 🐛 Allow json params to be defined from file
- ✨ Add `--full` to show full list of options on help page

## 0.4.13

- 🩹 Fix non-str object being casted to json

## 0.4.12

- 🩹 Allow ParamJson to have python object values, not only strings


## 0.4.11
- 🐛Fix the same param not allowed to add

## 0.4.10
- ✨Add _to_dict for parsed Namespace object

## 0.4.8
- Add kwargs to `to` and `copy` for Param

## 0.4.7
- Use basename in help for prog name by default
- Fix ignore_errors not ignoring the non-PyParamException errors

## 0.4.6
- Make sure switching # arugments of callbacks correctly
- Only print errors with help for callbaks to return exceptions, otherwise, raise them
- Make clean logger level name

## 0.4.5
- Change help_cmd to choice
-
## 0.4.4
- Don't use shared console for logging
- Allow command to be not provided.

## 0.4.3
- Allow default value of other types to be None
- Fix None value conversion at runtime

## 0.4.2
- Don't use `hasattr` for `__contains__` for Namespace, which allows override of `__getattr__`
- Move help_modifier to params construct
- Update HelpAssembler when command is reused.
- Allow completions for show=True only parameters
- Add kwargs of params to to_dict
- Fix fish completion shell code
- Fix prog update for Params
- Separate defaults of params and param to save size of dumped dict/file
- Add update (`__or__`, `__ior__`) for namespace
- Fix positional/command next to bool from cli
- Fix decendents of ns parameter are hidden from completions if the ns parameter is hidden.

## 0.4.1
- Add help_modifier argument for `params.parse` to modify help parameters and commands
- Add `params.to_file` to dump `params`
- Allow command reuse
- Add `force` for `params.from_file`, `params.from_dict` to force adding parameters and commands

## 0.4.0
- Allow parameter reuse
- Add shell completions support
- Add dir parameter type. It is not different as path parameter, but it show different complete candidate for shell completions.

## 0.3.2
- Fix required list parameter not raise error when on value provided

## 0.3.1
- Add default to from_arg

## 0.3.0
- Remodel the package with better APIs.
