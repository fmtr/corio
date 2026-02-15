from fmtr.tools import yaml_tools
from fmtr.tools.tests.helpers import SERIALIZATION_DATA


def test_yaml():
    """

    Simple YAML round trip test

    """
    expected = SERIALIZATION_DATA
    actual = yaml_tools.from_yaml(yaml_tools.to_yaml(expected))
    assert actual == expected
