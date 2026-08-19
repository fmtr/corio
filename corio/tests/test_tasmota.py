import sys

import pytest
from corio import Path
from corio.tasmota import config


def test_save_returns_mapping(monkeypatch):
    original_argv = sys.argv
    upstream = type("Upstream", (), {})()
    upstream.ExitCode = type("ExitCode", (), {"OK": 0})
    upstream.CONFIG = {}
    upstream.log = lambda *args, **kwargs: None
    upstream.parseargs = lambda: type("Args", (), {})()
    monkeypatch.setattr(config, "decode_config", upstream)
    monkeypatch.setattr(config, "_script_path", lambda: Path("/tmp/decode-config.py"))
    monkeypatch.setattr(config.Manager, "_read_device", lambda module: {"groupmapping": {"flag": 1}})

    assert config.Manager("tasmota.local").save() == {"flag": 1}
    assert sys.argv is original_argv


def test_output_is_logged(monkeypatch):
    upstream = type("Upstream", (), {})()
    upstream.ExitCode = type("ExitCode", (), {"OK": 0})
    upstream.CONFIG = {}
    upstream.log = lambda *args, **kwargs: None
    upstream.parseargs = lambda: type("Args", (), {})()
    monkeypatch.setattr(config, "decode_config", upstream)
    monkeypatch.setattr(config, "_script_path", lambda: Path("/tmp/decode-config.py"))

    def read_device(module):
        print("downloaded")
        print("decoded", file=sys.stderr)
        return {"groupmapping": {}}

    monkeypatch.setattr(config.Manager, "_read_device", read_device)
    records = []
    logger = type(
        "Logger",
        (),
        {
            "info": lambda _, message: records.append(("info", message)),
            "warning": lambda _, message: records.append(("warning", message)),
            "error": lambda _, message: records.append(("error", message)),
        },
    )()
    monkeypatch.setattr(config, "logger", logger)
    manager = config.Manager("tasmota.local")
    manager.save()

    assert records == [("info", "downloaded"), ("info", "decoded")]


def test_nonzero_upstream_exit_becomes_exception(monkeypatch):
    upstream = type("Upstream", (), {})()
    upstream.ExitCode = type("ExitCode", (), {"OK": 0})
    upstream.CONFIG = {}
    upstream.log = lambda *args, **kwargs: None
    upstream.parseargs = lambda: (_ for _ in ()).throw(SystemExit(11))
    monkeypatch.setattr(config, "decode_config", upstream)
    monkeypatch.setattr(config, "_script_path", lambda: Path("/tmp/decode-config.py"))

    with pytest.raises(config.DecodeConfigError, match="11") as error:
        config.Manager("192.0.2.1").save()

    assert error.value.exit_code == 11


def test_upstream_zero_exit_does_not_hide_logged_error(monkeypatch):
    upstream = type("Upstream", (), {})()
    upstream.ExitCode = type("ExitCode", (), {"OK": 0})
    upstream.CONFIG = {}

    def log(status=0, *args, **kwargs):
        raise SystemExit(0)

    upstream.log = log
    upstream.parseargs = lambda: type("Args", (), {})()
    monkeypatch.setattr(config, "decode_config", upstream)
    monkeypatch.setattr(config, "_script_path", lambda: Path("/tmp/decode-config.py"))

    def read_device(module):
        module.log(10, "host unavailable")

    monkeypatch.setattr(config.Manager, "_read_device", read_device)
    manager = config.Manager("missing.invalid")

    with pytest.raises(config.DecodeConfigError) as error:
        manager.save()

    assert error.value.exit_code == 10
    assert error.value.message == "host unavailable"
    assert error.value.messages == ["ERROR 10: host unavailable"]
    assert "host unavailable" in str(error.value)


def test_original_error_is_reraised_instead_of_system_exit(monkeypatch):
    upstream = type("Upstream", (), {})()
    upstream.ExitCode = type("ExitCode", (), {"OK": 0})
    upstream.CONFIG = {}
    upstream.log = lambda *args, **kwargs: (_ for _ in ()).throw(SystemExit(0))
    upstream.parseargs = lambda: type("Args", (), {})()
    monkeypatch.setattr(config, "decode_config", upstream)
    monkeypatch.setattr(config, "_script_path", lambda: Path("/tmp/decode-config.py"))

    original_error = ConnectionError("name resolution failed")

    def read_device(module):
        try:
            raise original_error
        except ConnectionError:
            module.log(22, "could not connect")

    monkeypatch.setattr(config.Manager, "_read_device", read_device)
    records = []
    logger = type(
        "Logger",
        (),
        {
            "info": lambda _, message: records.append(("info", message)),
            "warning": lambda _, message: records.append(("warning", message)),
            "error": lambda _, message: records.append(("error", message)),
        },
    )()
    monkeypatch.setattr(config, "logger", logger)
    manager = config.Manager("missing.invalid")

    with pytest.raises(ConnectionError) as raised:
        manager.save()

    assert raised.value is original_error
    assert records == [("error", "ERROR 22: could not connect")]
