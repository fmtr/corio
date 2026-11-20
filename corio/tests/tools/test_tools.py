from corio import tools


def test_identity():
    obj = {"a": 1}
    assert tools.identity(obj) is obj


def test_special_markers_and_empty_singleton():
    assert issubclass(tools.Empty, tools.Special)
    assert issubclass(tools.Raise, tools.Special)
    assert issubclass(tools.Auto, tools.Special)
    assert issubclass(tools.Required, tools.Special)
    assert isinstance(tools.EMPTY, tools.Empty)
