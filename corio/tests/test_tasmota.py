import sys
from importlib.metadata import PackageNotFoundError

import pytest
from corio import Path
from corio.tasmota import config


def test_missing_distribution_raises_module_not_found(monkeypatch):
    def missing_distribution(name):
        raise PackageNotFoundError(name)

    monkeypatch.setattr(config, "distribution", missing_distribution)

    with pytest.raises(ModuleNotFoundError) as error:
        config._script_path()

    assert error.value.name == "decode_config"


def test_save_returns_mapping(monkeypatch):
    original_argv = sys.argv
    upstream = type("Upstream", (), {})()
    upstream.ExitCode = type("ExitCode", (), {"OK": 0})
    upstream.CONFIG = {}
    upstream.log = lambda *args, **kwargs: None
    upstream.parseargs = lambda: type("Args", (), {})()
    monkeypatch.setattr(config, "decode_config", upstream)
    monkeypatch.setattr(config, "_script_path", lambda: Path("/tmp/decode-config.py"))
    monkeypatch.setattr(config.Manager, "_read_device", lambda self: {"groupmapping": {"flag": 1}})

    assert config.Manager("tasmota.local").read() == {"flag": 1}
    assert sys.argv is original_argv


def test_output_is_logged(monkeypatch):
    upstream = type("Upstream", (), {})()
    upstream.ExitCode = type("ExitCode", (), {"OK": 0})
    upstream.CONFIG = {}
    upstream.log = lambda *args, **kwargs: None
    upstream.parseargs = lambda: type("Args", (), {})()
    monkeypatch.setattr(config, "decode_config", upstream)
    monkeypatch.setattr(config, "_script_path", lambda: Path("/tmp/decode-config.py"))

    def read_device(self):
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
    manager.read()

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
        config.Manager("192.0.2.1").read()

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

    def read_device(self):
        config.decode_config.log(10, "host unavailable")

    monkeypatch.setattr(config.Manager, "_read_device", read_device)
    manager = config.Manager("missing.invalid")

    with pytest.raises(config.DecodeConfigError) as error:
        manager.read()

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

    def read_device(self):
        try:
            raise original_error
        except ConnectionError:
            config.decode_config.log(22, "could not connect")

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
        manager.read()

    assert raised.value is original_error
    assert records == [("error", "ERROR 22: could not connect")]
