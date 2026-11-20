import asyncio

import pytest
from pyrage import x25519

from corio import sec
from corio.constants import Constants
from corio.encrypt import EncryptorValues


def test_definition_casts_string_nodes_to_nodes():
    definition = sec.Definition(files=[], nodes=["*"])

    assert isinstance(definition.nodes[0], sec.Node)
    assert definition.nodes[0].glob == "*"
    assert definition.nodes[0].pattern is None


def test_definition_parses_complex_nodes_and_anchors_pattern():
    definition = sec.Definition(
        files=[],
        nodes=[{"glob": "app/password", "pattern": r"https?://user:(.*)@.*&token=(.*)"}],
    )

    node = definition.nodes[0]
    assert node.glob == "app/password"
    assert node.rx.fullmatch("https://user:alice@example.test&token=secret")
    assert not node.rx.search("prefix https://user:alice@example.test&token=secret")


def test_definition_nodes_defaults_to_empty():
    assert sec.Definition(files=[]).nodes == []


def test_definition_accepts_a_nullable_root_node():
    definition = sec.Definition(
        files=[],
        nodes=[{"glob": None, "pattern": r"user=(.*);token=(.*)"}],
    )

    assert definition.nodes[0].glob is None


def test_definition_accepts_a_root_opt_out_node():
    definition = sec.Definition(files=[], nodes=[{"glob": None, "pattern": False}])

    assert definition.nodes[0].pattern is False


def test_decrypt_mirrors_black_files_and_ignores_other_files(secrets_tree, monkeypatch):
    source = secrets_tree.decrypt_source
    target = secrets_tree.decrypt_target

    class _StubEncryptor:
        @staticmethod
        def decrypt(data):
            return data["payload"]

    decrypt = sec.Decrypt(source=source, target=target)
    monkeypatch.setattr(sec.Decrypt, "encryptor", _StubEncryptor())

    asyncio.run(decrypt.run())

    assert (target / "snapshot.red.yml").read_yaml() == {
        "credentials": {"token": "fixture-snapshot"}
    }
    assert (target / "nested" / "record.red.yml").read_yaml() == {
        "credentials": {"token": "fixture-record"}
    }
    assert (source / "snapshot.black.yml").read_yaml() == {
        "payload": {"credentials": {"token": "fixture-snapshot"}}
    }
    assert (source / "nested" / "record.black.yml").exists()
    assert (source / "notes.yml").read_yaml() == {"message": "not encrypted"}
    assert not (target / "notes.red.yml").exists()


def test_definition_paths_implicitly_end_in_red_yml(tmp_path):
    path_repo = sec.Path(tmp_path)
    path_red = path_repo / "proxy" / "one" / ".secrets" / "traefik.yaml.red.yml"
    path_red.parent.mkdirf()
    path_red.write_yaml({"email": "secret"})

    definition = sec.Definition(
        files=["proxy/*/.secrets/traefik.yaml"],
        nodes=["**/email"],
    )
    encrypt = sec.Encrypt()
    encrypt.config = type("Config", (), {"path_repo": path_repo})()

    assert encrypt.get_paths(definition) == [path_red]


def test_definition_paths_use_raw_file_when_red_file_does_not_exist(tmp_path):
    path_repo = sec.Path(tmp_path)
    path_raw = path_repo / "proxy" / "traefik.yaml"
    path_raw.parent.mkdirf()
    path_raw.write_yaml({"email": "secret"})

    definition = sec.Definition(files=["proxy/traefik.yaml"])
    encrypt = sec.Encrypt()
    encrypt.config = type("Config", (), {"path_repo": path_repo})()

    assert encrypt.get_paths(definition) == [path_raw]


def test_definition_paths_prefer_red_file_when_raw_and_red_files_exist(tmp_path):
    path_repo = sec.Path(tmp_path)
    path_raw = path_repo / "proxy" / "traefik.yaml"
    path_red = path_repo / "proxy" / "traefik.yaml.red.yml"
    path_raw.parent.mkdirf()
    path_raw.write_yaml({"email": "raw"})
    path_red.write_yaml({"email": "red"})

    definition = sec.Definition(files=["proxy/traefik.yaml"])
    encrypt = sec.Encrypt()
    encrypt.config = type("Config", (), {"path_repo": path_repo})()

    assert encrypt.get_paths(definition) == [path_red]


@pytest.mark.parametrize(
    ("scope_relative", "expected_directories"),
    [
        (".", {".", "workspace", "workspace/deep", "sibling"}),
        ("workspace", {"workspace", "workspace/deep"}),
        ("workspace/deep", {"workspace/deep"}),
    ],
)
@pytest.mark.parametrize("delete", [True, False])
def test_encrypt_scopes_each_source_type_to_current_directory(
    tmp_path,
    monkeypatch,
    scope_relative,
    expected_directories,
    delete,
):
    path_repo = sec.Path(tmp_path)
    path_scope = path_repo if scope_relative == "." else path_repo / scope_relative
    definition = sec.Definition(
        files=["**/settings.json", "**/covered.yml"],
        nodes=["*"],
    )

    class _StubEncryptor:
        @staticmethod
        def encrypt(data):
            return {
                key: "sealed" if key == "token" else value
                for key, value in data.items()
            }

        @staticmethod
        def decrypt(data):
            return {
                key: "plain" if key == "token" else value
                for key, value in data.items()
            }

    monkeypatch.setattr(sec.Definition, "encryptor", _StubEncryptor())

    source_files = []
    for relative_directory in (".", "workspace", "workspace/deep", "sibling"):
        path_directory = path_repo if relative_directory == "." else path_repo / relative_directory
        if relative_directory != ".":
            path_directory.mkdirf()
        data = {"token": "plain", "location": relative_directory}
        sources = (
            path_directory / "settings.json",
            path_directory / "covered.yml.red.yml",
            path_directory / "loose.yml.red.yml",
        )
        for path_source in sources:
            path_source.write_data(data)
            path_black = path_directory / f"{path_source.name.removesuffix('.red.yml')}.black.yml"
            source_files.append((path_source, path_black, data, relative_directory))

    monkeypatch.chdir(path_scope)
    encrypt = sec.Encrypt(delete=delete)
    encrypt.config = type("Config", (), {"path_repo": path_repo, "definitions": [definition]})()
    asyncio.run(encrypt.run())

    for path_source, path_black, data, relative_directory in source_files:
        is_in_scope = relative_directory in expected_directories
        assert path_black.exists() is is_in_scope
        if is_in_scope:
            assert path_black.read_yaml() == {"token": "sealed", "location": relative_directory}

        source_should_exist = not is_in_scope or not delete
        assert path_source.exists() is source_should_exist
        if source_should_exist:
            assert path_source.read_data() == data


def test_encrypt_cli_loads_repo_config_but_scopes_work_to_nested_cwd(secrets_tree, monkeypatch):
    tree = secrets_tree
    path_settings = tree.workspace / "settings.json"
    path_connection = tree.workspace / "connection.yml.red.yml"
    path_override = tree.workspace / "local" / "override.yml.red.yml"
    path_worker = tree.workspace / "jobs" / "worker.yml.red.yml"
    source_data = {
        path_settings: path_settings.read_json(),
        path_connection: path_connection.read_yaml(),
        path_override: path_override.read_yaml(),
        path_worker: path_worker.read_yaml(),
    }

    key = str(x25519.Identity.generate())
    monkeypatch.setenv(Constants.FMTR_AGE_KEY_KEY, key)
    monkeypatch.chdir(tree.workspace)

    cli = sec.Cli(_cli_parse_args=["encrypt"])
    asyncio.run(cli.encrypt.run())

    assert cli.path_repo == tree.repo
    decryptor = EncryptorValues(key=key)
    for path_source, data in source_data.items():
        path_black = path_source.parent / f"{path_source.name.removesuffix('.red.yml')}.black.yml"
        black_data = path_black.read_yaml()
        assert decryptor.is_encrypted(black_data["credentials"]["token"])
        assert decryptor.decrypt(black_data) == data
        assert not path_source.exists()

    assert (tree.workspace / "local" / "preserved.black.yml").read_yaml() == {
        "sentinel": "leave-unchanged"
    }
    assert (tree.workspace / "README.txt").read_text() == "ordinary file"
    assert (tree.archive / "settings.json").read_json()["credentials"]["token"] == "clear-archive"
    assert (tree.archive / "override.yml.red.yml").read_yaml()["credentials"]["token"] == "clear-maple"
    assert not (tree.archive / "settings.json.black.yml").exists()
    assert not (tree.archive / "override.yml.black.yml").exists()


@pytest.mark.parametrize(
    ("plain_value", "existing_value", "should_rewrite"),
    [
        ("amber", "enc:amber", False),
        ("amber", "amber", True),
        ("violet", "enc:amber", True),
    ],
)
def test_encrypt_reuses_only_aligned_unchanged_black_file(
    tmp_path,
    monkeypatch,
    plain_value,
    existing_value,
    should_rewrite,
):
    path_red = sec.Path(tmp_path) / "settings.yml.red.yml"
    path_black = sec.Path(tmp_path) / "settings.yml.black.yml"
    path_red.write_yaml({"token": plain_value})
    path_black.write_yaml({"token": existing_value})
    definition = sec.Definition(files=[], nodes=["*"])

    class _StubEncryptor:
        @staticmethod
        def encrypt(data):
            return {"token": f"enc:{data['token']}"}

        @staticmethod
        def decrypt(data):
            return {"token": data["token"].removeprefix("enc:")}

        @staticmethod
        def include(path):
            return True

        @staticmethod
        def is_encrypted(value):
            return value.startswith("enc:")

    monkeypatch.setattr(sec.Definition, "encryptor", _StubEncryptor())

    result = sec.Encrypt().process_file(path_red, definition)

    expected_black = {"token": f"enc:{plain_value}"}
    assert result == (path_black if should_rewrite else None)
    assert path_black.read_yaml() == expected_black
    assert not path_red.exists()


def test_encrypt_round_trip_failure_keeps_plaintext_and_writes_no_black_file(tmp_path, monkeypatch):
    path_red = sec.Path(tmp_path) / "settings.yml.red.yml"
    path_black = sec.Path(tmp_path) / "settings.yml.black.yml"
    plain = {"token": "amber"}
    path_red.write_yaml(plain)

    class _StubEncryptor:
        @staticmethod
        def encrypt(data):
            return {"token": "sealed"}

        @staticmethod
        def decrypt(data):
            return {"token": "different"}

    monkeypatch.setattr(sec.Definition, "encryptor", _StubEncryptor())

    with pytest.raises(ValueError):
        sec.Encrypt().process_file(path_red, sec.Definition(files=[], nodes=["*"]))

    assert path_red.read_yaml() == plain
    assert not path_black.exists()


@pytest.mark.parametrize(("preserve", "expected_mode"), [(True, 0o640), (False, 0o600)])
def test_decrypt_preserves_black_metadata_only_when_requested(
    tmp_path,
    monkeypatch,
    preserve,
    expected_mode,
):
    source = sec.Path(tmp_path / "source")
    target = sec.Path(tmp_path / "target")
    path_black = source / "settings.yml.black.yml"
    path_red = target / "settings.yml.red.yml"
    source.mkdirf()
    target.mkdirf()
    path_black.write_yaml({"token": "sealed"})
    path_red.write_yaml({"token": "stale"})
    path_black.chmod(0o640)
    path_red.chmod(0o600)
    sec.os.utime(path_black, (2_000_000, 2_000_000))
    sec.os.utime(path_red, (1_000_000, 1_000_000))
    chown_calls = []
    monkeypatch.setattr(sec.os, "chown", lambda *args: chown_calls.append(args))

    class _StubEncryptor:
        @staticmethod
        def decrypt(data):
            return {"token": "plain"}

    monkeypatch.setattr(sec.Decrypt, "encryptor", _StubEncryptor())

    result = sec.Decrypt(source=source, target=target, preserve=preserve).process_file(path_black)

    metadata = path_black.stat()
    expected_chown_calls = [(path_red, metadata.st_uid, metadata.st_gid)] if preserve else []
    assert result == path_red
    assert path_red.read_yaml() == {"token": "plain"}
    assert sec.stat.S_IMODE(path_red.stat().st_mode) == expected_mode
    assert chown_calls == expected_chown_calls


def test_decrypt_restore_writes_original_name_and_format(tmp_path, monkeypatch):
    source = sec.Path(tmp_path / "source")
    target = sec.Path(tmp_path / "target")
    path_black = source / "credentials.json.black.yml"
    path_black.parent.mkdirf()
    path_black.write_yaml({"token": "ciphertext"})

    class _StubEncryptor:
        @staticmethod
        def decrypt(data):
            return {"token": "plaintext"}

    decrypt = sec.Decrypt(source=source, target=target, restore=True)
    monkeypatch.setattr(sec.Decrypt, "encryptor", _StubEncryptor())

    asyncio.run(decrypt.run())

    path_restored = target / "credentials.json"
    assert path_restored.read_json() == {"token": "plaintext"}
    assert not (target / "credentials.json.red.yml").exists()


@pytest.mark.parametrize(
    ("target_state", "force", "expected_write"),
    [
        ("missing", False, True),
        ("older", False, False),
        ("same", False, False),
        ("different", False, True),
        ("older", True, True),
        ("same", True, True),
    ],
)
def test_decrypt_target_update_policy(
    tmp_path,
    monkeypatch,
    target_state,
    force,
    expected_write,
):
    source = sec.Path(tmp_path / "source")
    target = sec.Path(tmp_path / "target")
    source.mkdirf()
    target.mkdirf()
    path_black = source / "settings.yml.black.yml"
    path_red = target / "settings.yml.red.yml"
    path_black.write_yaml({"token": "sealed"})
    original_target = {
        "older": {"token": "keep"},
        "same": {"token": "plain"},
        "different": {"token": "stale"},
    }.get(target_state)
    target_timestamp = None
    if original_target:
        path_red.write_yaml(original_target)
        target_timestamp = 3_000_000 if target_state == "older" else 1_000_000
        sec.os.utime(path_red, (target_timestamp, target_timestamp))
    sec.os.utime(path_black, (2_000_000, 2_000_000))

    class _StubEncryptor:
        @staticmethod
        def decrypt(data):
            return {"token": "plain"}

    decrypt = sec.Decrypt(source=source, target=target, force=force)
    monkeypatch.setattr(sec.Decrypt, "encryptor", _StubEncryptor())

    result = decrypt.process_file(path_black)

    assert result == (path_red if expected_write else None)
    if expected_write:
        assert path_red.read_yaml() == {"token": "plain"}
        assert path_red.stat().st_mtime != target_timestamp
    else:
        assert path_red.read_yaml() == original_target
        assert path_red.stat().st_mtime == target_timestamp
    assert path_black.read_yaml() == {"token": "sealed"}


def test_decrypt_defaults_source_and_target_to_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    decrypt = sec.Decrypt()

    assert decrypt.source == sec.Path(tmp_path)
    assert decrypt.target == sec.Path(tmp_path)
    assert decrypt.restore is False
    assert decrypt.force is False
    assert decrypt.preserve is False


def test_encrypt_cli_parses_delete_option_without_secrets_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    cli = sec.Cli(_cli_parse_args=["encrypt", "--delete", "false"])

    assert cli.encrypt.delete is False


def test_decrypt_cli_parses_documented_options_without_secrets_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    cli = sec.Cli(
        _cli_parse_args=[
            "decrypt",
            "--source", str(tmp_path / "source"),
            "--target", str(tmp_path / "target"),
            "--restore", "true",
        ]
    )

    assert cli.definitions == []
    assert cli.decrypt.source == sec.Path(tmp_path / "source")
    assert cli.decrypt.target == sec.Path(tmp_path / "target")
    assert cli.decrypt.restore is True
