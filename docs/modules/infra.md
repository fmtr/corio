# infra
`from corio import infra`

`infra` is the release/build orchestration layer used by `corio` projects.

Core objects:

- `Project`: package metadata + runtime release context
- `Repository`: git operations (`fetch`, tagging, push flow)
- `Stack`: container build/deploy definitions (development and production variants)
- `Releaser`: version increment, package build/upload, docs deploy flow
- `infrastructure.api.Api`: FastAPI surface for release/build/recreate operations

Production images built by `Stack` run their entrypoint as the unprivileged `user` account (UID 1000). Files accessed by the process must be readable or writable by that UID as needed.

The production container CLI defaults to `podman`. Select Docker for a project in its metadata when the build should use Docker:

```toml
[tool.corio.metadata]
container_cli = "docker"
container_host = "ssh://user@host"
```

A non-null `container_host` also enables production image builds during the release flow. The host is passed directly to the container client, so SSH endpoints target a remote Docker Engine without requiring a Docker context.

Install:

```bash
pip install "corio[infra]" --upgrade
```

## Typical Usage

```python
from corio import infra

project = infra.Project("corio")
project.releaser.run(build=False, release=True, cache=True)
```

The same release flow is available from the command line:

```bash
corio infra release --name corio
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

1. version increment and release metadata updates
2. editable dependency availability checks and configured tox tests
3. commit, tag, and push
4. optional container build/push
5. package build/upload
6. docs deploy
7. remove generated release artifacts from the worktree, including build/test caches, coverage data, and Python bytecode caches; coverage configuration is preserved

Before tox starts, the release checks each configured `[tool.corio.metadata].editables` entry ([editable packages](path.md#editable-packages)), in order, using its pinned sibling-repository version. It polls PyPI for up to 10 minutes; if a version does not appear, the release stops without starting tests.

When a current pre-release version has no matching Git tag, the release flow stops rather than assuming that version can be safely reused. Resolve the release state or pin the intended stable base explicitly before retrying.
