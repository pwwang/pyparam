Parameters can also be loaded from a configuration file that is supported by [`python-simpleconf`][17]

`sample.ini`
```ini
[default]
opt1 = 1
opt1.desc = 'This is option 1'
[profile1]
opt1 = 2
```
```python
params._loadFile('sample.ini', profile = 'default')
print(params.dict())
# {'opt1': 1}
# profile = 'profile1'
# {'opt1': 2}
```

[17]: https://github.com/pwwang/simpleconf