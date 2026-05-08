from corio import jsn
from corio.path import Path
from corio.tests.helpers import SERIALIZATION_DATA


def test_json():
    """

    Simple YAML round trip test

    """
    expected = SERIALIZATION_DATA
    actual = jsn.from_json(jsn.to_json(expected))
    assert actual == expected


def test_json_path_round_trip(tmp_path):
    expected = SERIALIZATION_DATA
    path_json = Path(tmp_path / "serialization_test.json")

    path_json.write_json(expected)
    actual = path_json.read_json()

    assert actual == expected
