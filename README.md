# inspect_runtime
a python API-exploration tool.  inspect your code at runtime for certain string values.  generates a list of all code that will return your targeted value.

___

# Scopes explicitly searched:  
- thread stackframes
- locals
- any other object as specified by you

___

## Examples
`python3.6 -i -m inspect_runtime`

### locals example
```
>>> local_var = "teststr"
>>> get_paths_containing_string_in_locals(local_var, locals())
[ValueFinder(locator="locals()['local_var']", key='local_var', value='teststr')]
```

### thread stackframes example
```
>>> get_paths_containing_string_in_threadstack(local_var)
[ValueFinder(locator='[get_paths_containing_string_in_locals(target_str, val.frame.f_locals) for idx, val in enumerate(inspect.getouterframes(inspect.currentframe(), 2)) if "pydev" not in val.filename][\'target_str\']', key='target_str', value='teststr'), 
ValueFinder(locator='[get_paths_containing_string_in_locals(target_str, val.frame.f_locals) for idx, val in enumerate(inspect.getouterframes(inspect.currentframe(), 2)) if "pydev" not in val.filename][\'local_var\']', key='local_var', value='teststr')]
```

### nested attributes of a custom-class example
```
>>> class TestClass:
...     clsval = "testclsval"
... 
>>> testcls = TestClass()
>>> setattr(testcls, "__fakeinner__.doublefakeinner__", "deepval")
>>> get_all_paths_containing_string_in_nested_objects(testcls, "deepval", _result=[], max_depth=2)
[path_value(locator='.__dict__', value="{'__fakeinner__.doublefakeinner__': 'deepval'}"), 
path_value(locator='.__fakeinner__.doublefakeinner__', value='deepval'), 
path_value(locator='.__reduce__()', value='<built-in method __reduce__ of TestClass object at 0x7f9782bc7c18>()'), 
path_value(locator='.__reduce_ex__()', value='<built-in method __reduce_ex__ of TestClass object at 0x7f9782bc7c18>()')]
>>> testcls.__reduce_ex__()
(<function _reconstructor at 0x7f9782b9f488>, (<class '__main__.TestClass'>, <class 'object'>, None), {'__fakeinner__.doublefakeinner__': 'deepval'})
```
