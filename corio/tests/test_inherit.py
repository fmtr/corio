from dataclasses import dataclass

from corio.inherit import Inherit


class Parent:
    def __init__(self, value: str):
        self.value = value

    def ping(self):
        return f"parent:{self.value}"


@dataclass
class Endpoint:
    path: str


class InheritedEndpoint(Inherit[Parent], Endpoint):
    pass


def test_inherit_falls_back_to_parent_attributes():
    endpoint = InheritedEndpoint(Parent("ok"), path="/ping")
    assert endpoint.ping() == "parent:ok"
    assert endpoint.inherit_parent.value == "ok"


def test_inherit_initialises_secondary_base_in_multiple_inheritance():
    endpoint = InheritedEndpoint(Parent("ok"), path="/health")
    assert endpoint.path == "/health"
