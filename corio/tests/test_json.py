from corio import jsn
from corio.tests.helpers import SERIALIZATION_DATA


def test_json():
    """

    Simple YAML round trip test

    """
    expected = SERIALIZATION_DATA
    actual = jsn.from_json(jsn.to_json(expected))
    assert actual == expected
