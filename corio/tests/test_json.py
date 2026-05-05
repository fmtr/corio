from corio import json
from corio.tests.helpers import SERIALIZATION_DATA


def test_json():
    """

    Simple YAML round trip test

    """
    expected = SERIALIZATION_DATA
    actual = json.from_json(json.to_json(expected))
    assert actual == expected
