# logs
`from corio import logs`

Logging setup and instrumentation helpers. Logfire and OpenTelemetry are included in Corio's base dependencies, so the `logging` extra is not required.

## Default logger

`from corio import logger` returns Corio's configured Logfire logger. Its service name and version come from Corio's package metadata.

## Configure a logger for your package

Pass your package's `PackagePaths` to `from_paths` to derive the logger's service identity and version from its metadata instead of hard-coding them:

```python
from corio.logs import from_paths
from corio.path import PackagePaths, Path

logger = from_paths(PackagePaths(Path.cwd()))
```

Set `FMTR_OBS_API_KEY` to enable Corio's OTLP exporters for traces, metrics, and logs. Without the key, those custom exporters are not configured.
