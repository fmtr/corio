from corio import toml
from corio.path import Path


def test_from_toml_and_table_access():
    data = toml.from_toml(
        """
        [tool.corio]
        value = 1
        """
    )

    assert toml.get_table(data, ("tool", "corio")) == {"value": 1}
    assert toml.get_table(data, ("tool", "missing")) is None
    assert toml.get_table({"a": 1}, ("a",)) is None


def test_ensure_table_creates_nested_dicts():
    data = {"tool": {"corio": 1}}
    table = toml.ensure_table(data, ("tool", "corio", "tests"))

    assert table == {}
    assert isinstance(data["tool"]["corio"], dict)
    assert data["tool"]["corio"]["tests"] == {}


def test_toml_path_round_trip(tmp_path):
    expected = {
        "tool": {"corio": {"value": 1, "name": "demo"}},
        "list": [1, 2, 3],
    }
    path_toml = Path(tmp_path / "serialization_test.toml")

    path_toml.write_toml(expected)
    actual = path_toml.read_toml()

    assert actual == expected
