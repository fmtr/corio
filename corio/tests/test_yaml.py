from corio import yaml
from corio.tests.helpers import SERIALIZATION_DATA


def test_yaml():
    """

    Simple YAML round trip test

    """
    expected = SERIALIZATION_DATA
    actual = yaml.from_yaml(yaml.to_yaml(expected))
    assert actual == expected
