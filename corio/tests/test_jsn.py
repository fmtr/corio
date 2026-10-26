from dataclasses import dataclass
from datetime import date, datetime, time

import pytest

from corio import jsn
from corio.path import Path
from corio.tests.helpers import SERIALIZATION_DATA


@dataclass
class SerializationData:
    name: str
    created: date
    updated: datetime
    at: time


def test_json():
    """

    Simple YAML round trip test

    """
    expected = SERIALIZATION_DATA
    actual = jsn.from_json(jsn.to_json(expected))
    assert actual == expected


def test_json_dataclass_and_time_values():
    value = SerializationData(
        name="example",
        created=date(2026, 1, 2),
        updated=datetime(2026, 1, 2, 3, 4, 5),
        at=time(6, 7, 8),
    )

    assert jsn.from_json(jsn.to_json(value)) == {
        "name": "example",
        "created": "2026-01-02",
        "updated": "2026-01-02T03:04:05",
        "at": "06:07:08",
    }


def test_json_serializes_paths():
    assert jsn.from_json(jsn.to_json(Path("example"))) == "example"


def test_json_rejects_unsupported_values():
    class Unsupported:
        pass

    with pytest.raises(TypeError, match="Unsupported"):
        jsn.to_json(Unsupported())


def test_json_path_round_trip(tmp_path):
    expected = SERIALIZATION_DATA
    path_json = Path(tmp_path / "serialization_test.json")

    path_json.write_json(expected)
    actual = path_json.read_json()

    assert actual == expected
