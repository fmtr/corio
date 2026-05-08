import random

from corio import name


def test_name_lists_are_non_empty():
    assert len(name.get_left()) > 0
    assert len(name.get_right()) > 0


def test_get_name_tuple_or_string():
    random.seed(0)
    left_right = name.get(sep=None)
    assert isinstance(left_right, tuple)
    assert len(left_right) == 2

    random.seed(0)
    text = name.get(sep="-")
    assert isinstance(text, str)
    assert "-" in text
