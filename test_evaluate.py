import pytest

import expression_object
from expression_object import get_or_create_expression_object

basic_value_dict = {
    "a" : True,
    "b" : True,
    "c" : False,
    "d" : False}

expression_object.basic_value_dict = basic_value_dict

simple_exprs_and_results = [("a and b", True),
                            ("a or b", True),
                            ("a and c", False),
                            ("(a and c) or b", True),
                            ("!(a and b)", False),
                            ("!a", False),
                            ("!a or b", True),
                            ("!(!(a and b))", True),
                            ("!!a", True)]

@pytest.mark.parametrize( ("expr_str", "expected_value"),
            simple_exprs_and_results)
def test_evaluate_expressions(expr_str, expected_value):
    exp_obj = get_or_create_expression_object(expr_str)
    assert exp_obj.is_true() == expected_value
