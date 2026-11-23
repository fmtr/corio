import logging
import os
from types import SimpleNamespace

import logfire
import pytest
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from corio.constants import Constants
from corio.logs import Configurer, Signals, from_paths


def test_post_init_applies_property_defaults():
    configurer = Configurer(name="sample-service", version="4.2.1")

    assert configurer.stream == configurer.stream_default
    assert configurer.environment == configurer.environment_default
    assert configurer.level == configurer.level_default


def test_service_version_defaults_for_current_package():
    from corio.paths import paths

    configurer = Configurer(name=paths.name)

    assert configurer.service_version == paths.metadata.version_dev


def test_from_paths_returns_configured_logger(monkeypatch):
    from corio.paths import paths

    captured = {}
    marker = object()

    def configure(**options):
        captured.update(options)
        return marker

    monkeypatch.setattr(logfire, "configure", configure)
    monkeypatch.delenv(Constants.FMTR_OBS_API_KEY_KEY, raising=False)

    configured_logger = from_paths(paths)

    assert configured_logger is marker
    assert captured["service_name"] == paths.name
    assert captured["service_version"] == paths.metadata.version_dev


def test_service_version_is_required_for_other_services():
    configurer = Configurer(name="sample-service")

    with pytest.raises(ValueError, match="A version is required"):
        _ = configurer.service_version


def test_explicit_service_version_is_used():
    configurer = Configurer(name="sample-service", version="4.2.1")

    assert configurer.service_version == "4.2.1"


def test_otlp_exporters_are_configured_for_each_signal():
    configurer = Configurer(
        name="sample-service",
        version="4.2.1",
        host="telemetry.example.invalid",
        key="synthetic-token",
        org="sample-org",
        stream="sample-stream",
    )

    assert [signal.value for signal in Signals] == ["traces", "metrics", "logs"]
    assert configurer.endpoint_mask == "https://telemetry.example.invalid/api/sample-org/v1/{signal}"
    assert configurer.traces_endpoint == "https://telemetry.example.invalid/api/sample-org/v1/traces"
    assert configurer.metrics_endpoint == "https://telemetry.example.invalid/api/sample-org/v1/metrics"
    assert configurer.logs_endpoint == "https://telemetry.example.invalid/api/sample-org/v1/logs"
    assert configurer.headers == {
        "Authorization": "Basic synthetic-token",
        "stream-name": "sample-stream",
    }

    span_processors = configurer.span_processors
    metric_readers = configurer.metric_readers
    log_record_processors = configurer.log_record_processors
    assert len(span_processors) == 1
    assert len(metric_readers) == 1
    assert len(log_record_processors) == 1
    assert isinstance(span_processors[0], BatchSpanProcessor)
    assert isinstance(metric_readers[0], PeriodicExportingMetricReader)
    assert isinstance(log_record_processors[0], BatchLogRecordProcessor)
    span_processors[0].shutdown()
    log_record_processors[0].shutdown()


def test_missing_api_key_disables_custom_exporters(monkeypatch):
    monkeypatch.delenv(Constants.FMTR_OBS_API_KEY_KEY, raising=False)
    configurer = Configurer(name="sample-service", version="4.2.1")

    assert configurer.span_processors == []
    assert configurer.metrics_options.additional_readers == []
    assert configurer.advanced_options.log_record_processors == []


def test_configure_passes_all_pipeline_options_without_mutating_environment(monkeypatch):
    captured = {}
    marker = object()

    def configure(**options):
        captured.update(options)
        return marker

    monkeypatch.setattr(logfire, "configure", configure)
    monkeypatch.setenv(Constants.FMTR_OBS_API_KEY_KEY, "synthetic-token")
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT", raising=False)
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_LOGS_ENDPOINT", raising=False)
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_METRICS_ENDPOINT", raising=False)

    configurer = Configurer(
        name="sample-service",
        version="4.2.1",
        host="telemetry.example.invalid",
        key="synthetic-token",
        org="sample-org",
        stream="sample-stream",
    )

    assert configurer.logger is marker
    assert captured["service_name"] == "sample-service"
    assert captured["service_version"] == "4.2.1"
    assert captured["send_to_logfire"] is False
    assert captured["additional_span_processors"] == configurer.span_processors
    assert captured["metrics"] is configurer.metrics_options
    assert captured["advanced"] is configurer.advanced_options
    assert "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT" not in os.environ
    assert "OTEL_EXPORTER_OTLP_LOGS_ENDPOINT" not in os.environ
    assert "OTEL_EXPORTER_OTLP_METRICS_ENDPOINT" not in os.environ
    captured["additional_span_processors"][0].shutdown()
    captured["advanced"].log_record_processors[0].shutdown()
    captured["metrics"].additional_readers[0].shutdown()


def test_console_and_scrubbing_options_come_from_configurer_properties():
    configurer = Configurer(name="sample-service", version="4.2.1", level=logging.INFO)

    assert configurer.otel_level_name == "info"
    assert configurer.console_options.min_log_level == "info"
    assert configurer.scrubbing_options.callback(SimpleNamespace(value="visible")) == "visible"
