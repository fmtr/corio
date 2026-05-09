from corio import yml
from corio.path import Path
from corio.tests.helpers import SERIALIZATION_DATA


def test_yaml():
    """

    Simple YAML round trip test

    """
    expected = SERIALIZATION_DATA
    actual = yml.from_yaml(yml.to_yaml(expected))
    assert actual == expected


def test_yaml_path_round_trip(tmp_path):
    expected = SERIALIZATION_DATA | {
        "text": "Sed ut perspiciatis unde omnis iste natus error sit voluptatem accusantium doloremque laudantium \n" * 10
    }
    path_yaml = Path(tmp_path / "serialization_test.yaml")

    path_yaml.write_yaml(expected)
    actual = path_yaml.read_yaml()

    assert actual == expected
