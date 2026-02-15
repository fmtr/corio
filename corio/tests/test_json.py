from corio import json_tools
from corio.tests.helpers import SERIALIZATION_DATA


def test_json():
    """

    Simple YAML round trip test

    """
    expected = SERIALIZATION_DATA
    actual = json_tools.from_json(json_tools.to_json(expected))
    assert actual == expected
