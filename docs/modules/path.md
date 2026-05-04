# `from corio import path`

`path` is one of the core modules in `corio`. It extends `pathlib.Path` and provides package-aware path resolution helpers used throughout the rest of the library.

Primary exports:

- `Path`: enhanced path object with convenience readers/writers (`json`, `yaml`, `toml`, `.env`, inferred `read_data`/`write_data`)
- `PackagePaths`: canonical package/repo metadata and path discovery
- `AppPaths`: appdirs wrapper (`path.app` extra)

## What Is Useful Here

- `Path.read_data()` / `Path.write_data(obj)` infer serializer by suffix:
  - `.json` -> JSON
  - `.yaml` / `.yml` -> YAML
  - `.toml` -> TOML
  - `.env` -> dotenv map
  - unknown -> text
- `Path.find_up(name)` walks up parent directories for repo-root style config lookup.
- `Path.mkdirf()` is a `parents=True, exist_ok=True` convenience.
- `PackagePaths().metadata` gives strongly-typed access to `tool.corio.metadata` from package `pyproject`.
- WSL absolute Windows paths are auto-converted when running under WSL.

## Examples

```python
from corio import Path

path = Path("settings.yaml")
config = path.read_data()  # same as read_yaml() here

out = Path("build/runtime.toml")
out.parent.mkdirf()
out.write_data({"name": "corio", "enabled": True})
runtime = out.read_data()
```

```python
from corio import PackagePaths

paths = PackagePaths()
print(paths.repo)
print(paths.metadata.version)
print(paths.metadata.description)
```

```python
from corio import Path

path_secrets = Path.cwd().find_up(".secrets.yml")
print(path_secrets)
```

## Serializer Methods

`Path` also exposes explicit methods when you do not want extension inference:

- `read_json()` / `write_json()`
- `read_yaml()` / `write_yaml()`
- `read_toml()` / `write_toml()`
- `read_env()` / `write_env()`

