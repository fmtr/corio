from enum import auto

from corio.enums import MapEnum


class Priority(MapEnum):
    LOW = auto(), "A low priority."
    HIGH = auto(), "A high priority."


def test_map_enum_generates_ids_from_member_names():
    assert Priority.LOW.value == "LOW"
    assert Priority.HIGH.value == "HIGH"


def test_map_enum_members_have_descriptions():
    assert Priority.LOW.description == "A low priority."


def test_map_enum_descriptions_lists_members():
    assert Priority.descriptions == "LOW: A low priority.\nHIGH: A high priority."
