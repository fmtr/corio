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

The production container CLI defaults to `podman`. Set `container_cli` when a project needs a different compatible CLI. A configured `container_host` enables production image builds during the release flow and identifies the remote container host:

```toml
[tool.corio.metadata]
container_cli = "podman"
container_host = "ssh://user@host"
```

The host is passed directly to the configured container client, so an SSH endpoint can be used without a CLI context. The build log reports the configured container target.

Install:

```bash
pip install "corio[infra]" --upgrade
```

## Typical Usage

```python
from corio import infra

project = infra.Project("corio")
project.releaser.run(release=True)
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

## Generated Test Environments

Before running tests, the release workflow generates tox environments from the test package layout and dependency metadata. By default, it creates one development environment (`dev`) and one production environment (`prod`) for the full test suite. Set `test_envs = true` under `[tool.corio.metadata]` to generate environments for each package module with a matching `tests/<module>/` package instead:

```toml
[tool.corio.metadata]
test_envs = true
```

Each `tests/<module>/` package can contain multiple `test_*.py` files. Pytest receives the package directory and collects its test modules recursively.

Per-module environments are named `<module>.dev` and `<module>.prod`. Development environments use the source checkout and local editable dependencies; production environments install the package. The generated production environments make up tox's default `env_list`, which is what the release workflow runs. Development environment names are recorded in `[tool.corio.test-envs].dev` for source-tree testing.

## Release Flow (high-level)

`releaser.run(...)` orchestrates:

1. increment the version and generate `pyproject.toml` release metadata used by tests
2. run configured tox tests, retrying dependency-resolution failures for up to 10 minutes
3. after tests pass, update add-on and changelog release metadata
4. commit, tag, and push
5. optional container build/push
6. package build/upload
7. docs deploy
8. remove generated release artifacts from the worktree, including build/test caches, coverage data, and Python bytecode caches; coverage configuration is preserved

Test failures block both stable and pre-releases. On failure, the generated `pyproject.toml` is restored; add-on and changelog updates have not yet run. The release changes are staged only after all incrementors succeed.

The release-start log message names the project and the Corio runtime version used.

If tox fails with `No solution found when resolving dependencies`, the release retries tox every 10 seconds for up to 10 minutes. Other dependency-installation failures and test failures stop the release immediately.

When a current pre-release version has no matching Git tag, the release flow stops rather than assuming that version can be safely reused. Resolve the release state or pin the intended stable base explicitly before retrying.
