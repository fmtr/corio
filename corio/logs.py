import logging
from dataclasses import dataclass
from enum import StrEnum
from functools import cached_property
from typing import ClassVar, cast

import logfire
# The OTLP HTTP log exporter currently has no public module-level export.
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk._logs import LogRecordProcessor
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics.export import MetricReader, PeriodicExportingMetricReader
from opentelemetry.sdk.trace import SpanProcessor
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from corio import env, path
from corio.constants import Constants
from corio.paths import paths


class Signals(StrEnum):
    TRACES = "traces"
    METRICS = "metrics"
    LOGS = "logs"


@dataclass
class Configurer:
    """Configure Logfire and OTLP exporters for a service."""

    OTEL_TO_NATIVE: ClassVar[dict[int, int]] = {
        1: 1,  # trace
        3: 5,  # debug
        5: 10,  # debug (canonical)
        6: 13,  # warn
        8: 17,  # error
        9: 20,  # info
        10: 23,  # notice
        11: 25,  # success/loguru
        13: 30,  # warning
        17: 40,  # error
        21: 50,  # fatal
    }

    name: str
    version: str | None = None
    host: str = Constants.FMTR_OBS_HOST
    key: str | None = None
    org: str = Constants.ORG_NAME
    stream: str | None = None
    environment: str | None = None
    level: int | None = None

    @property
    def stream_default(self) -> str | None:
        if env.IS_DEV:
            return Constants.DEVELOPMENT
        return None

    @property
    def environment_default(self) -> str:
        if env.IS_DEV:
            return Constants.DEVELOPMENT
        return Constants.PRODUCTION

    @property
    def level_default(self) -> int:
        if env.IS_DEV:
            return logging.DEBUG
        return logging.INFO

    def __post_init__(self) -> None:
        if self.stream is None:
            self.stream = self.stream_default
        if self.environment is None:
            self.environment = self.environment_default
        if self.level is None:
            self.level = self.level_default

    @classmethod
    def from_paths(cls, paths: path.PackagePaths) -> logfire.Logfire:
        configurer = cls(name=paths.name, version=paths.metadata.version_dev)
        return configurer.logger

    @cached_property
    def service_version(self) -> str:
        if self.version is not None:
            return self.version
        if self.name != paths.name:
            raise ValueError(f"A version is required for service {self.name!r}")
        return paths.metadata.version_dev

    @cached_property
    def api_key(self) -> str | None:
        return self.key or env.get(Constants.FMTR_OBS_API_KEY_KEY, default=None)

    @cached_property
    def stream_name(self) -> str:
        return self.stream or self.name

    @cached_property
    def base_url(self) -> str:
        return f"https://{self.host}/api/{self.org}"

    @cached_property
    def endpoint_mask(self) -> str:
        return f"{self.base_url}/v1/{{signal}}"

    @cached_property
    def headers(self) -> dict[str, str]:
        headers = {"stream-name": self.stream_name}
        if self.api_key:
            headers["Authorization"] = f"Basic {self.api_key}"
        return headers

    @cached_property
    def traces_endpoint(self) -> str:
        return self.endpoint_mask.format(signal=Signals.TRACES)

    @cached_property
    def metrics_endpoint(self) -> str:
        return self.endpoint_mask.format(signal=Signals.METRICS)

    @cached_property
    def logs_endpoint(self) -> str:
        return self.endpoint_mask.format(signal=Signals.LOGS)

    @cached_property
    def span_processors(self) -> list[SpanProcessor]:
        if not self.api_key:
            return []
        return [
            BatchSpanProcessor(
                OTLPSpanExporter(endpoint=self.traces_endpoint, headers=self.headers)
            )
        ]

    @cached_property
    def metric_readers(self) -> list[MetricReader]:
        if not self.api_key:
            return []
        return [
            PeriodicExportingMetricReader(
                OTLPMetricExporter(endpoint=self.metrics_endpoint, headers=self.headers)
            )
        ]

    @cached_property
    def metrics_options(self) -> logfire.MetricsOptions:
        return logfire.MetricsOptions(additional_readers=self.metric_readers)

    @cached_property
    def log_record_processors(self) -> list[LogRecordProcessor]:
        if not self.api_key:
            return []
        return [
            BatchLogRecordProcessor(
                OTLPLogExporter(endpoint=self.logs_endpoint, headers=self.headers)
            )
        ]

    @cached_property
    def advanced_options(self) -> logfire.AdvancedOptions:
        # Logfire currently exposes custom log export through an experimental processor hook.
        return logfire.AdvancedOptions(log_record_processors=self.log_record_processors)

    @cached_property
    def otel_level_name(self) -> str:
        from logfire._internal import constants

        level = cast(int, self.level)
        otel_level = constants.LOGGING_TO_OTEL_LEVEL_NUMBERS[level]
        return constants.NUMBER_TO_LEVEL[otel_level]

    @cached_property
    def console_options(self) -> logfire.ConsoleOptions:
        return logfire.ConsoleOptions(
            colors="always",
            include_timestamps=env.IS_DEV,
            min_log_level=self.otel_level_name,
        )

    @staticmethod
    def scrubber(match: logfire.ScrubMatch) -> str:
        return match.value

    @cached_property
    def scrubbing_options(self) -> logfire.ScrubbingOptions:
        return logfire.ScrubbingOptions(callback=self.scrubber)

    @cached_property
    def logger(self) -> logfire.Logfire:
        configured_logger = logfire.configure(
            service_name=self.name,
            service_version=self.service_version,
            environment=self.environment,
            send_to_logfire=False,
            console=self.console_options,
            scrubbing=self.scrubbing_options,
            additional_span_processors=self.span_processors,
            metrics=self.metrics_options,
            advanced=self.advanced_options,
        )
        return configured_logger

    @property
    def current_level(self) -> str:
        return self.logger.config.console.min_log_level

    @classmethod
    def native_level_from_otel(cls, otel_name: str) -> int:
        from logfire._internal import constants

        otel_level = constants.LEVEL_NUMBERS[otel_name]
        native_level = cls.OTEL_TO_NATIVE[otel_level]
        return native_level


def sanitize(message: str) -> str:
    """

    Sanitize a log line for brace-style formatters.

    """
    return message.rstrip().replace("{", "{{").replace("}", "}}")


def get_logger_names() -> list[str]:
    """

    Fetch current native logger names.

    """
    return list(logging.getLogger().manager.loggerDict.keys())


from_paths = Configurer.from_paths
logger = from_paths(paths)
