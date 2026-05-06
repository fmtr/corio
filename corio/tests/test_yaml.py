from corio import yml
from corio.tests.helpers import SERIALIZATION_DATA


def test_yaml():
    """

    Simple YAML round trip test

    """
    expected = SERIALIZATION_DATA
    actual = yml.from_yaml(yml.to_yaml(expected))
    assert actual == expected
