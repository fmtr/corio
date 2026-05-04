# `from corio import infra`

`infra` is the release/build orchestration layer used by `corio` projects.

Core objects:

- `Project`: package metadata + runtime release context
- `Repository`: git operations (`fetch`, tagging, push flow)
- `Stack`: container build/deploy definitions (development and production variants)
- `Releaser`: version increment, package build/upload, docs deploy flow
- `infrastructure_tools.api.Api`: FastAPI surface for release/build/recreate operations

Install:

```bash
pip install "corio[infra]" --upgrade
```

## Typical Usage

```python
from corio import infra

project = infra.Project("corio")
project.releaser.run(increment=True, build=False, release=True, cache=True)
```

## API Usage

`infra.Api` exposes release/build/recreate endpoints and is used by infra wrapper repos:

```python
from corio import infra

infra.Api.launch()
```

## Docs Release Expectations

Docs release expects:

- `docs/` content in repo root
- `tool.corio.metadata.docs.nav` in `pyproject.toml`

`ReleaseDocumentation` builds MkDocs configuration dynamically from project metadata, so nav structure in `pyproject` is part of the release contract.

## Release Flow (high-level)

`releaser.run(...)` orchestrates:

1. version increment + git/tag flow
2. optional container build/push
3. package build/upload
4. docs deploy

