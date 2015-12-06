import pytest
from expression_object import find_closing_paren
from expression_object import intelligent_split_or
from expression_object import intelligent_split_and
from expression_object import strip_expression
from expression_object import get_clean_expression_and_inversion

def test_find_closing_paren():
    assert find_closing_paren("(a and b)",0) == 8
    assert find_closing_paren("a and (b or c)",0) == -1
    assert find_closing_paren("a and (b or c)",6) == 13

def test_intelligent_split_or():
    assert intelligent_split_or("a or b or c") == ["a","b","c"]
    assert intelligent_split_or("a or b and c") == ["a", "b and c"]
    assert intelligent_split_or("a or b or c or") == ["a", "b", "c"]
    assert intelligent_split_or("a or b or (c and d)") == ["a", "b", "c and d"]
    assert intelligent_split_or("(a or b) and (c or d)") == ["(a or b) and (c or d)"]
    assert intelligent_split_or("(a and b) and (c or d)") == ["(a and b) and (c or d)"]

def test_intelligent_split_and():
    assert intelligent_split_and("a and b") == ["a", "b"]
    assert intelligent_split_and("a and b and c") == ["a", "b", "c"]
    assert intelligent_split_and("(a and b)") == ["a", "b"]
    assert intelligent_split_and("a and (b and c)") == ["a", "b and c"]
    assert intelligent_split_and("(a and b) and (b and c)") == ["a and b", "b and c"]
    assert intelligent_split_and("(a and b)and c") == ["a and b", "c"]

def test_strip_expression():
    assert strip_expression(" a and b") == "a and b"
    assert strip_expression("(a and b)") == "a and b"
    assert strip_expression("( a and b )") == "a and b"
    assert strip_expression("((a and b))") == "a and b"
    assert strip_expression("( (a and b))") == "a and b"
    assert strip_expression("((a and b) or c )") == "(a and b) or c"
    assert strip_expression("!(a and b)") == "!(a and b)"

def test_get_clean_expression_and_inversion():
    assert get_clean_expression_and_inversion(" a and b") == ("a and b", False)
    assert get_clean_expression_and_inversion("!a and b") == ("!a and b", False)
    assert get_clean_expression_and_inversion("!(a and b)") == ("a and b", True)
    assert get_clean_expression_and_inversion("!(a and b) and c") == ("!(a and b) and c", False)
    assert get_clean_expression_and_inversion("(!(a and b))") == ("a and b", True)
    assert get_clean_expression_and_inversion("(!(!(a and b)))") == ("a and b", False)
    assert get_clean_expression_and_inversion("!a") == ("a", True)
    assert get_clean_expression_and_inversion("!!a") == ("a", False)
