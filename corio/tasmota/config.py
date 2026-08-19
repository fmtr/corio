"""

In-process wrapper around the ``decode-config`` script.

The distribution installs a single script named ``decode-config.py`` outside
site-packages, rather than an importable package. This module locates that
script through distribution metadata and calls its internal conversion and
HTTP functions. No subprocess or intermediate file is involved.

"""

from __future__ import annotations

import sys
from collections.abc import Mapping
from contextlib import redirect_stderr, redirect_stdout
from importlib import util
from importlib.metadata import PackageNotFoundError, distribution
from io import StringIO
from threading import Lock
from types import ModuleType
from typing import Any

from corio import Path, logger

_UPSTREAM_LOCK = Lock()


class DecodeConfigError(RuntimeError):
    """

    Error reported by decode-config without an underlying Python exception.

    """

    def __init__(self, exit_code: int | str | None, message: str | None = None):
        self.exit_code = exit_code
        self.message = message
        self.messages: list[str] = []
        detail = f": {message}" if message else ""
        super().__init__(f"decode-config failed with exit code {exit_code!r}{detail}")


def _script_path() -> Path:
    """

    Return the installed ``decode-config.py`` script path.

    """
    try:
        dist = distribution("decode-config")
    except PackageNotFoundError as error:
        raise RuntimeError("The 'decode-config' distribution is not installed") from error

    for installed_file in dist.files or ():
        if Path(str(installed_file)).name == "decode-config.py":
            script = Path(dist.locate_file(installed_file)).resolve()
            if script.is_file():
                return script
    raise RuntimeError("The installed 'decode-config' distribution has no decode-config.py")


def _load_upstream() -> ModuleType:
    """

    Import the hyphenated script without running its CLI body.

    """
    script = _script_path()
    spec = util.spec_from_file_location("_corio_decode_config", script)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import decode-config from {script}")
    module = util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


decode_config = _load_upstream()


class Manager:
    """

    Back up and restore the configuration of one Tasmota host.

    """

    def __init__(self, host: str):
        self.host = host

    def _log_output(self, lines: list[str]) -> None:
        """

        Log output captured from decode-config at the corresponding level.

        """
        for line in lines:
            if line.startswith("ERROR"):
                logger.error(line)
            elif line.startswith("WARNING"):
                logger.warning(line)
            else:
                logger.info(line)

    def save(self) -> dict[str, Any]:
        """

        Download and decode the host configuration as a dictionary.

        """
        return self._call(self._save)

    def load(self, config: Mapping[str, Any]) -> None:
        """

        Encode and upload a configuration dictionary to the host.

        """
        self._call(self._load, config)

    def _call(self, operation, *args):
        # Upstream relies on module globals and parseargs relies on sys.argv, so operations are
        # serialized and mutable state is reset for every call.
        with _UPSTREAM_LOCK:
            module = decode_config
            previous_argv = sys.argv
            output = StringIO()
            decode_error = None
            reported_exit_code = module.ExitCode.OK
            reported_error_message = None
            upstream_log = module.log

            def tracking_log(status=0, *log_args, **log_kwargs):
                nonlocal reported_error_message, reported_exit_code
                if isinstance(status, int) and status != module.ExitCode.OK:
                    reported_exit_code = status
                    if "msg" in log_kwargs:
                        reported_error_message = str(log_kwargs["msg"])
                    elif log_args:
                        reported_error_message = str(log_args[0])
                    print(
                        f"ERROR {status}: {reported_error_message or ''}",
                        file=sys.stderr,
                    )
                    original_error = sys.exception()
                    if original_error is not None:
                        raise original_error
                    raise DecodeConfigError(status, reported_error_message)
                return upstream_log(status, *log_args, **log_kwargs)

            module.log = tracking_log
            try:
                sys.argv = [str(_script_path()), "--source", self.host]
                with redirect_stdout(output), redirect_stderr(output):
                    try:
                        module.ARGS = module.parseargs()
                        module.ARGS.httpsource = self.host
                        module.ARGS.source = None
                        module.ARGS.verbose = True
                        module.CONFIG = {}
                        module.EXIT_CODE = module.ExitCode.OK
                        return operation(module, *args)
                    except SystemExit as error:
                        exit_code = error.code
                        if exit_code in (None, 0):
                            exit_code = reported_exit_code
                        if exit_code != module.ExitCode.OK:
                            raise DecodeConfigError(
                                exit_code, reported_error_message
                            ) from error
            except DecodeConfigError as error:
                decode_error = error
                error.messages = output.getvalue().splitlines()
                raise
            finally:
                lines = output.getvalue().splitlines()
                if decode_error is None:
                    self._log_output(lines)
                sys.argv = previous_argv

    @staticmethod
    def _read_device(module: ModuleType) -> dict[str, Any]:
        encoded = module.pull_http()
        if not encoded:
            raise DecodeConfigError(module.ExitCode.DOWNLOAD_CONFIG_ERROR)

        config: dict[str, Any] = {"encode": encoded}
        if module.config_has_settings_header(encoded):
            config["header"] = encoded[:16]
            config["decode"] = module.decrypt_encrypt(encoded[16:], has_header=True)
        else:
            config["header"] = None
            config["decode"] = module.decrypt_encrypt(encoded, has_header=False)
        config["info"] = module.get_config_info(config["decode"])
        # Several upstream converters ignore their argument and consult this module global instead.
        module.CONFIG = config
        config["valuemapping"] = module.bin2mapping(config, raw=True)
        config["groupmapping"] = module.bin2mapping(config, raw=False)
        return config

    @classmethod
    def _save(cls, module: ModuleType) -> dict[str, Any]:
        return cls._read_device(module)["groupmapping"]

    @classmethod
    def _load(cls, module: ModuleType, mapping: Mapping[str, Any]) -> None:
        current = cls._read_device(module)
        decoded = module.mapping2bin(current, dict(mapping), "<mapping>")
        if decoded is None:
            raise DecodeConfigError(module.EXIT_CODE)

        encoded = module.decrypt_encrypt(
            decoded, has_header=len(decoded) > current["info"]["template_size"]
        )
        if len(encoded) > current["info"]["template_size"]:
            header = bytearray(module.TASM_FILE_SETTINGS.encode())
            header.extend(bytearray(16 - len(header)))
            module.struct.pack_into("<H", header, 14, len(encoded) + 16)
            encoded = header + encoded

        # Avoid rebooting/uploading when the supplied mapping makes no change.
        if encoded == current["encode"]:
            return
        error_code, _ = module.push_http(encoded)
        if error_code:
            raise DecodeConfigError(error_code)
