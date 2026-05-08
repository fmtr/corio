from contextlib import nullcontext

import corio.caching as caching_module
from corio.caching import Disk, TLRU


def test_disk_nested_dump(tmp_path):
    cache = Disk(tmp_path / "cache")

    cache.setdefault("svc", Disk)["enabled"] = True
    cache["count"] = 2

    dumped = cache.dump()
    assert dumped["count"] == 2
    assert dumped["svc"]["enabled"] is True


def test_tlru_expire_with_custom_timer(monkeypatch):
    class DummyLogger:
        @staticmethod
        def span(_):
            return nullcontext()

        @staticmethod
        def debug(_):
            return None

    monkeypatch.setattr(caching_module, "logger", DummyLogger())

    now = [0]
    cache = TLRU(maxsize=4, timer=lambda: now[0], ttu_static=5, desc="test")
    cache["k1"] = "v1"

    assert "k1" in cache
    now[0] = 6
    expired = cache.expire()

    assert expired == [("k1", "v1")]
    assert "k1" not in cache


def test_tlru_evicts_when_maxsize_exceeded(monkeypatch):
    class DummyLogger:
        @staticmethod
        def span(_):
            return nullcontext()

        @staticmethod
        def debug(_):
            return None

    monkeypatch.setattr(caching_module, "logger", DummyLogger())

    now = [0]
    cache = TLRU(maxsize=2, timer=lambda: now[0], ttu_static=100, desc="test")
    cache["k1"] = "v1"
    cache["k2"] = "v2"
    cache["k3"] = "v3"

    assert len(cache) == 2
    assert "k3" in cache


def test_disk_deep_setdefault_and_data_property(tmp_path):
    cache = Disk(tmp_path / "cache")
    cache.setdefault("c", Disk).setdefault("c1", Disk)["subkey"] = 0.1
    cache["c"]["test"] = False
    cache["val"] = 123
    cache.setdefault("b", Disk)["value3"] = [789, True]

    dumped = cache.data
    assert dumped["c"]["c1"]["subkey"] == 0.1
    assert dumped["c"]["test"] is False
    assert dumped["b"]["value3"] == [789, True]
    assert dumped["val"] == 123
