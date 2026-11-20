from dataclasses import dataclass

import pytest

from corio.path import Path


@dataclass
class SecretsTree:
    repo: Path
    workspace: Path
    archive: Path
    decrypt_source: Path
    decrypt_target: Path


@pytest.fixture
def secrets_tree(tmp_path) -> SecretsTree:
    repo = Path(tmp_path)
    workspace = repo / "components" / "cedar"
    archive = repo / "components" / "maple"
    decrypt_source = repo / "restore" / "incoming"
    decrypt_target = repo / "restore" / "outgoing"

    for directory in (
        workspace / "local",
        workspace / "jobs",
        archive,
        decrypt_source / "nested",
    ):
        directory.mkdirf()

    (repo / ".secrets.yml").write_yaml(
        {
            "definitions": [
                {
                    "files": [
                        "components/cedar/settings.json",
                        "components/cedar/connection.yml",
                    ],
                    "nodes": ["credentials/token"],
                }
            ]
        }
    )

    (workspace / "settings.json").write_json(
        {
            "credentials": {"token": "clear-settings", "user": "sample"},
            "endpoint": "https://cedar.invalid",
        }
    )
    (workspace / "connection.yml.red.yml").write_yaml(
        {"credentials": {"token": "clear-connection"}, "port": 8412}
    )
    (workspace / "local" / "override.yml.red.yml").write_yaml(
        {"credentials": {"token": "clear-override"}, "enabled": True}
    )
    (workspace / "jobs" / "worker.yml.red.yml").write_yaml(
        {"credentials": {"token": "clear-worker"}, "queue": {"concurrency": 3}}
    )
    (workspace / "local" / "preserved.black.yml").write_yaml(
        {"sentinel": "leave-unchanged"}
    )
    (workspace / "README.txt").write_text("ordinary file")

    (archive / "settings.json").write_json(
        {"credentials": {"token": "clear-archive"}, "endpoint": "https://maple.invalid"}
    )
    (archive / "override.yml.red.yml").write_yaml(
        {"credentials": {"token": "clear-maple"}, "enabled": False}
    )

    (decrypt_source / "snapshot.black.yml").write_yaml(
        {"payload": {"credentials": {"token": "fixture-snapshot"}}}
    )
    (decrypt_source / "nested" / "record.black.yml").write_yaml(
        {"payload": {"credentials": {"token": "fixture-record"}}}
    )
    (decrypt_source / "notes.yml").write_yaml({"message": "not encrypted"})

    return SecretsTree(
        repo=repo,
        workspace=workspace,
        archive=archive,
        decrypt_source=decrypt_source,
        decrypt_target=decrypt_target,
    )
