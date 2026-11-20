from contextlib import nullcontext
from dataclasses import dataclass

import pytest

patterns = pytest.importorskip("corio.patterns", exc_type=ImportError)


class DummyLogger:
    @staticmethod
    def span(_):
        return nullcontext()

    @staticmethod
    def debug(_):
        return None


@dataclass
class HostKey(patterns.Key):
    FILLS = {"name": r"[a-z]+"}
    host: str


def test_alt_orders_longer_patterns_first():
    assert patterns.alt("a", "aa", "aaa") == "(?:aaa|aa|a)"


def test_transformer_single_pass(monkeypatch):
    monkeypatch.setattr(patterns, "logger", DummyLogger())

    transformer = patterns.Transformer(
        items=[
            patterns.Item(
                source=HostKey(host=r"api\.{name}\.local"),
                target=HostKey(host="edge.{name}.local"),
            )
        ],
        default=None,
    )

    actual = transformer.get(HostKey(host="api.demo.local"))

    assert isinstance(actual, HostKey)
    assert actual.host == "edge.demo.local"


def test_transformer_default_when_no_match(monkeypatch):
    monkeypatch.setattr(patterns, "logger", DummyLogger())

    transformer = patterns.Transformer(items=[], default="missing")
    actual = transformer.get(HostKey(host="no-match.local"))

    assert actual == "missing"


def test_transformer_recursive_loop_detection(monkeypatch):
    monkeypatch.setattr(patterns, "logger", DummyLogger())

    key_a = HostKey(host="a.local")
    key_b = HostKey(host="b.local")
    transformer = patterns.Transformer(
        is_recursive=True,
        items=[
            patterns.Item(source=HostKey(host="a.local"), target=key_b),
            patterns.Item(source=HostKey(host="b.local"), target=key_a),
        ],
    )

    with pytest.raises(patterns.RewriteCircularLoopError):
        transformer.get(key_a)
