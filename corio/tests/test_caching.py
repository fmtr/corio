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
