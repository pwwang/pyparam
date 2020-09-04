A most common use of `pyparam` is to parse the values from command line. Parameters will be matched and values will be consumed until the end of the command line. Values will be finally compiled into a namespace.

!!! Note

	In this documentation, We are using `paramter` to specifically refer to the parameter that is defined with `pyparam`. For the items from command line, we call them `arguments`

## Argument name prefix

By default, the prefix is `auto`, meaning that for short names (length <= 1), it is `-`; while for long ones (length > 1), it is `--`.

You can specify your own prefix. Then all the names will be sharing the same prefix this way.

## Argument with attached value
