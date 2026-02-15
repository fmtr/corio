import aiomqtt
import logging
from dataclasses import dataclass, asdict
from fmtr.tools.logging_tools import logger, get_current_level, get_native_level_from_otel
from paho.mqtt.client import CleanStartOption, MQTT_CLEAN_START_FIRST_ONLY
from typing import Literal, Self

LOGGER = logging.getLogger("mqtt")
LOGGER.handlers.clear()
LOGGER.addHandler(logger.LogfireLoggingHandler())
LOGGER.propagate = False


@dataclass
class Args:
    """

    The (serialisable subset of the) init args for Client (e.g. for init via Pydantic Settings)

    """
    hostname: str
    port: int = 1883
    username: str | None = None
    password: str | None = None
    identifier: str | None = None
    clean_session: bool | None = None
    transport: Literal["tcp", "websockets", "unix"] = "tcp"
    timeout: float | None = None
    keepalive: int = 60
    bind_address: str = ""
    bind_port: int = 0
    clean_start: CleanStartOption = MQTT_CLEAN_START_FIRST_ONLY
    max_queued_incoming_messages: int | None = None
    max_queued_outgoing_messages: int | None = None
    max_inflight_messages: int | None = None
    max_concurrent_outgoing_calls: int | None = None
    tls_insecure: bool | None = None




class Client(aiomqtt.Client):
    """

    Client stub

    """

    LOGGER = LOGGER
    SYNC_LOG_LEVEL = False
    Args = Args

    def __init__(self, *args, **kwargs):
        """

        Seems a little goofy to sync with logfire on every init, but unsure how to do it better.

        """
        if self.SYNC_LOG_LEVEL:
            self.sync_log_level()
        super().__init__(*args, **kwargs)

    def sync_log_level(self):
        """

        Sync log level with logfire, which might have changed since handler set.

        """
        level = get_current_level(logger)
        level_no = get_native_level_from_otel(level)
        self.LOGGER.setLevel(level_no)

    @classmethod
    def from_args(cls, args_obj: Args, **kwargs) -> Self:
        """

        Initialise from Args dataclass.

        """
        args = asdict(args_obj) | kwargs
        return cls(**args)

class Will(aiomqtt.Will):
    """

    Will stub

    """
