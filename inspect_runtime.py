import inspect
from collections import namedtuple

ValueFinder = namedtuple("ValueFinder", ["locator", "key", "value"])


def get_attribute_paths_containing_string(target_object, target_str, search_exact_word=False):
    """
    :param target_object: object to inspect during runtime
    :param target_str: :type str: string to search for
    :param search_exact_word: :type bool: if True, only values containing nothing but the find_value will be returned, else any value just containing the str will be returned.
    :return: a namedtuple(locator, value).  Running exec or eval on the locator in the same namespace should return the object containing the target_str.
    """
    members = inspect.getmembers(target_object)

    if search_exact_word:
        # finer-grained search that matches by full word, wrap the string in single quotes i.e. "\'yourstring\'"
        matches = [ValueFinder("[x for x in members if ("'" + target_str + "'") in str(x)]", target_str, x)
                   for x in members if ("\'" + target_str + "\'") in str(x)]
    else:
        # coarse-grained search.  check if target_str is anywhere in the attribute
        matches = [ValueFinder("x for x in inspect.getmembers(target_object) if target_str in str(x)", target_str, x)
                   for x in inspect.getmembers(target_object) if target_str in str(x)]

    return matches


def get_paths_containing_string_in_locals(target_str, locals_dict, locals_dict_ref_str="locals()"):
    """
    Get paths to anything in the locals namespace that contains the target string.
    :param target_str: string to search for
    :param locals_dict: the locals() dictionary.  In most cases, this should just be locals()
    :param locals_dict_ref_str: the string represenation of the locals_dict argument.  This will be used in returning the path to any matching values.
    :return: a namedtuple(locator, value).  Running exec or eval on the locator in the same namespace should return the object containing the target_str.
    """

    def conditions(key, val):
        return (str(val).__contains__(target_str)) and (key[0] != '_')

    matches = []
    for k, v in locals_dict.items():
        try:
            if conditions(k, v):
                matches.append(ValueFinder(locals_dict_ref_str + "['" + str(k) + "']", k, str(v)))
        except AttributeError:
            # This is a common exception and likely not much to worry about.  This code iterates over all attributes
            # of a dict looking for simple string matches and so runs into AttributeErrors.
            pass

    return matches


def get_paths_containing_string_in_threadstack(target_str, stack_context=2):
    """
    Get paths to datastructures containing string in the threadstack.  This excludes stackframes in modules external to the project
    :param target_str: string to search for
    :param stack_context: maximum outer scope of stacks to check
    :return: a namedtuple(locator, value).  Running exec or eval on the locator in the same namespace should return the object containing the target_str.
    """
    frames = []
    list_of_frames = [
        get_paths_containing_string_in_locals(target_str,
                                              val.frame.f_locals,
                                              locals_dict_ref_str="[get_paths_containing_string_in_locals(target_str, val.frame.f_locals) for idx, "
                                                                  "val in enumerate(inspect.getouterframes(inspect.currentframe(), "
                                                                  "2)) if \"pydev\" not in val.filename]")
        for idx, val in enumerate(inspect.getouterframes(inspect.currentframe(), stack_context))
        if "pydev" not in val.filename]

    for x in list_of_frames:
        for y in x:
            frames.append(y)
    return frames


def get_all_paths_containing_string(target_str, locals_dict, other_objects_to_inspect=None):
    """
    This searches locals(), all stackframes (but ignores frames triggered outside of this project's modules) and
    within any other objects provided in other_objects_to_inspect.

    :param target_str: the value you want to find
    :param locals_dict: a dictionary of locals().  Probably most cases, passing 'locals()'
    :param other_objects_to_inspect: :type list: (optional) any objects outside of locals or frames that you want to inspect
    for values
    :return: list of namedtuples(locator,key,find_value). An example of this is the ValueFinder tuple.
    :chains_into: __eval_all_locators
    """
    all_matches = []
    all_matches.extend(get_paths_containing_string_in_locals(target_str, locals_dict))
    all_matches.extend(get_paths_containing_string_in_threadstack(target_str))
    if other_objects_to_inspect:
        [all_matches.extend(get_attribute_paths_containing_string(other_object, target_str)) for other_object in
         other_objects_to_inspect]

    return all_matches


def get_all_categorized_paths_containing_string(target_str, locals_dict, other_objects_to_inspect=None):
    """
    Get all paths to datastructures containing the target_str.  Exact same results as get_all_paths_containing_string but categorized.
    :param target_str: the value you want to find
    :param locals_dict: a dictionary of locals().  Probably most cases, passing 'locals()'
    :param other_objects_to_inspect: :type list: (optional) any objects outside of locals or frames that you want to inspect for values
    :return: list of namedtuples(frames, inspections, locals) and within each of those fields, instances of
    namedtuples(locator,key,find_value). An example of this is the ValueFinder tuple.
    :chains_into: into __eval_all_locators.  For example, a raw eval can be applied(result.locals[0].locator)
    """
    matches_found = namedtuple("matches_found", ["locals", "frames", "inspections"])
    inspect_members_filtered_by_string = []

    locals_filtered_by_string = get_paths_containing_string_in_locals(target_str, locals_dict=locals_dict)
    frames_filtered_by_string = get_paths_containing_string_in_threadstack(target_str)

    if other_objects_to_inspect:
        [inspect_members_filtered_by_string.extend(get_attribute_paths_containing_string(other_object, target_str)) for
         other_object in other_objects_to_inspect]

    return matches_found(locals=locals_filtered_by_string, frames=frames_filtered_by_string,
                         inspections=inspect_members_filtered_by_string)


def __eval_all_locators(input_list, return_exec=False, return_exec_name="evaluated_locators"):
    """
    :param input_list: :type list of namedtuple(locator,key,value). An example of this is the ValueFinder tuple
    :param return_exec: :type boolean: flag for whether to return a code string that can be run through exec(*)
    :return: If return_executable is false, returns a list of all the locators run.  This often returns the actual
    object that the string was found in. if return_executable is true, this function runs nothing and just returns a
    string of code that can be run as an arg to the exec function.

    After running the exec function on this arg, a variable called evaluated_locators will be referenceable through
    the locals dictionary using return_exec_name's actual value as the key i.e. by default, locals()['evaluated_locators']
    """
    executable_code = return_exec_name + " = []\n" \
                                         "for x in " + repr(input_list) + ":\n" \
                                         "  " + return_exec_name + ".append(eval(x.locator))"
    try:
        if not return_exec:
            exec(executable_code)
            return locals()[return_exec_name]
    except KeyError:
        import traceback
        traceback.print_last()
        print("Key not found in this scope.  "
              "Consider using this function with the return_exec flag instead to run the function in the proper scope.")

    else:
        return executable_code


def get_all_paths_containing_string_in_nested_objects(object_ut, target_str, _result, max_depth=2, _path_string="", _current_depth=0):
    """
    Search the attributes of an object for target_str and the attributes of those attributes up to max_depth.
    :param object_ut:  object under test.  The object to inspect for the target_str
    :param target_str:  string to search for
    :param _result:  Use result=[] unlesss you require advanced usage.  This holds a running tally of results through
    recursive cycles.  Setting this to [] in the signature will change behaviour
    :param max_depth: max depth to recursively search attributes of attributes
     due to how python handles variable-default defined in the signature during recursion.
    :param _path_string:  Internal.  This holds a running tally of the datastructure's path through recursive cycles.
    :param _current_depth:  Internal.  This holds a running tally of the investigation-depth through recursive cycles.
    :return: a namedtuple(locator, value) of all objects containing target_str.  Running exec or eval on the locator in
    the same namespace should return the object containing the target_str.
    """
    tuple_inspected = inspect.getmembers(object_ut)
    destructive_callables = ["__clear__", "__setattr__", "__init__", "__init_subclass__", "__delattr__", "__call__"]
    path_value = namedtuple("path_value", ["locator", "value"])

    _current_depth += 1
    if _current_depth > max_depth:
        return _result

    if hasattr(tuple_inspected, "__iter__"):
        for v in tuple_inspected:
            try:
                attr = getattr(eval("object_ut" + _path_string), v[0])

                if callable(attr) and (v[0] not in destructive_callables):
                    postfix = "()"
                    candidate_str = str(attr())
                else:
                    postfix = ""
                    candidate_str = str(attr)

                if target_str in candidate_str:
                    _result.append(path_value(_path_string + "." + str(v[0]) + postfix, str(v[1]) + postfix))
                if (_current_depth + 1) <= max_depth:
                    _result = get_all_paths_containing_string_in_nested_objects(attr, target_str, _result=_result,
                                                                                _path_string=_path_string + "." + v[0] + postfix,
                                                                                _current_depth=_current_depth)

            except:
                # Many exceptions can be expected here
                # as this evaluates almost all attributes of a given object without knowing much about them.
                pass
    return _result
