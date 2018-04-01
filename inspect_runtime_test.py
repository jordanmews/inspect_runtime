from .inspect_runtime import get_paths_containing_string_in_locals, __eval_all_locators, \
    get_all_paths_containing_string, get_all_categorized_paths_containing_string, get_all_paths_containing_string_in_nested_objects, ValueFinder
import pytest


def test_eval_all_locators(test_method_inside_locals_scope=None):
    # Create some local var, methods and references too them.
    # Expected Result is they are found inside of locals()
    # Methods Under test: get_paths_containing_string_in_locals, eval

    # Setup
    local_test_var = "teststring"

    def testmethodname():
        pass

    testmethodref = testmethodname.__name__

    # Search the local runtime for all instances of your string
    locals_filtered_by_string = get_paths_containing_string_in_locals(local_test_var, locals_dict=locals())
    locals_filtered_by_string.extend(get_paths_containing_string_in_locals(testmethodref, locals_dict=locals()))

    # Test the results through a function that exists in the same namespace that the variables were gathered from.

    # The method to accomplish this was make the inspect_runtime.eval_all_locators function return executable code
    # that could be run within any other namespace.

    # More details - the below exec assigns to a variable. This requires that a variable of the
    # same name can NOT previously exist, else the exec will fail to overwrite the value in the locals() namespace.
    # The exec function can write to the locals scope, but not the function scope (For some
    # reason unknown to me at this time).  The variable can only be referenced through locals()['mykey'].  BUT,
    # if a variable with the exact same name already exists in the function scope.  Any attempts to create/modify a
    # var of the same name in the locals scope will fail silently.  The value that was set in the in the function's
    # scope gets priority and makes it immutable to the exec function.  So for those reasons, return_exec_key is used
    #  to store a string of the same name as the variable that will later store the return value of the exec function.
    return_exec_key = "return_exec_testname"
    if test_method_inside_locals_scope:
        return_exec_function = __eval_all_locators(locals_filtered_by_string, return_exec=False)
    else:
        return_exec_function = __eval_all_locators(locals_filtered_by_string, return_exec=True, return_exec_name=return_exec_key)

    exec(return_exec_function)

    assert len(locals()[return_exec_key]) > 0
    assert len([x for x in locals()[return_exec_key] if local_test_var in str(x)]) > 0
    assert len([x for x in locals()[return_exec_key] if testmethodref in str(x)]) > 0
    assert len([x for x in locals()[return_exec_key] if callable(x)]) > 0


def test_get_valuefinders_rawlist():
    assert str(get_all_paths_containing_string("module", locals(), [dict, tuple])).__contains__("module")


def test_get_valuefinders_categorized(populate_locals):
    testclass = "newval"

    assert len(get_all_categorized_paths_containing_string(testclass, locals(), [dict, tuple]).frames) > 0
    assert len(get_all_categorized_paths_containing_string(TestClass.testval, locals(), [TestClass]).inspections) > 0
    assert len(get_all_categorized_paths_containing_string(testclass, locals(), [TestClass]).locals) > 0


def locator_test_helper(object_ut, target_str, expected_fail=False):
    result = []
    result = get_all_paths_containing_string_in_nested_objects(object_ut, target_str, _result=result)

    if not expected_fail:
        assert len(result) > 0
    for x in result:
        try:
            assert str(eval("object_ut" + x.locator)).__contains__(target_str)
        except:
            print(str(x.value) + " not found at " + str(x.locator) + "  Was this value found in a different scope?")


def test_locators_are_returning_desired_values():
    object_ut = TestClass()
    locator_test_helper(object_ut, "TestClass")

    # target string exists in the second level of attributes ie.. x.__class__.__func__
    level2_target_str = "findme_in_second_level_of_attributes"
    object_ut.possiblepaths_source_class_or_module = level2_target_str
    locator_test_helper(object_ut, level2_target_str)

    # target string does not exist
    locator_test_helper(object_ut, "notoutthere", expected_fail=True)


class TestClass:
    possiblepaths_source_class_or_module = None
    testval = "testval"


@pytest.fixture
def populate_locals():
    local_test_var = "teststring"
    def testmethodname():
        pass
    testmethodref = testmethodname.__name__
