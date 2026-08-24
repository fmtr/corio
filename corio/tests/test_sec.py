from corio import sec


def test_decrypt_mirrors_source_tree_into_target(tmp_path, monkeypatch):
    source = sec.Path(tmp_path / "source")
    target = sec.Path(tmp_path / "target")
    path_black = source / "a" / "b" / ".env.black.yml"
    path_black.parent.mkdirf()
    path_black.write_yaml({"API_KEY": "ciphertext"})

    class _Encryptor:
        @staticmethod
        def decrypt(data):
            return {"API_KEY": "plaintext"}

    decrypt = sec.Decrypt(source=source, target=target)
    monkeypatch.setattr(sec.Decrypt, "encryptor", _Encryptor())

    decrypt.run()

    assert (target / "a" / "b" / ".env.red.yml").read_data() == {"API_KEY": "plaintext"}


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


def test_encrypt_maps_red_name_to_black_name(tmp_path, monkeypatch):
    path_red = sec.Path(tmp_path) / "credentials.json.red.yml"
    path_red.write_yaml({"token": "plaintext"})
    definition = sec.Definition(files=[], nodes=["*"])

    class _Encryptor:
        @staticmethod
        def encrypt(data):
            return {"token": "ciphertext"}

        @staticmethod
        def decrypt(data):
            return {"token": "plaintext"}

    monkeypatch.setattr(sec.Definition, "encryptor", _Encryptor())

    actual = sec.Encrypt().process_file(path_red, definition)

    assert actual == sec.Path(tmp_path) / "credentials.json.black.yml"
    assert not path_red.exists()


def test_encrypt_can_keep_red_file(tmp_path, monkeypatch):
    path_red = sec.Path(tmp_path) / "credentials.json.red.yml"
    path_red.write_yaml({"token": "plaintext"})
    definition = sec.Definition(files=[], nodes=["*"])

    class _Encryptor:
        @staticmethod
        def encrypt(data):
            return {"token": "ciphertext"}

        @staticmethod
        def decrypt(data):
            return {"token": "plaintext"}

    monkeypatch.setattr(sec.Definition, "encryptor", _Encryptor())

    sec.Encrypt(delete=False).process_file(path_red, definition)

    assert path_red.exists()


def test_decrypt_can_preserve_black_metadata_on_target(tmp_path, monkeypatch):
    path_red = sec.Path(tmp_path) / "credentials.json.red.yml"
    path_black = sec.Path(tmp_path) / "credentials.json.black.yml"
    path_red.write_yaml({"token": "plaintext"})
    path_black.write_yaml({"token": "ciphertext"})
    path_red.chmod(0o600)
    path_black.chmod(0o640)
    chown_calls = []
    monkeypatch.setattr(sec.os, "chown", lambda *args: chown_calls.append(args))

    sec.Decrypt(preserve=True).preserve_red(path_red, path_black)

    metadata = path_black.stat()
    assert sec.stat.S_IMODE(path_red.stat().st_mode) == 0o640
    assert chown_calls == [(path_red, metadata.st_uid, metadata.st_gid)]


def test_decrypt_restore_writes_original_name_and_format(tmp_path, monkeypatch):
    source = sec.Path(tmp_path / "source")
    target = sec.Path(tmp_path / "target")
    path_black = source / "credentials.json.black.yml"
    path_black.parent.mkdirf()
    path_black.write_yaml({"token": "ciphertext"})

    class _Encryptor:
        @staticmethod
        def decrypt(data):
            return {"token": "plaintext"}

    decrypt = sec.Decrypt(source=source, target=target, restore=True)
    monkeypatch.setattr(sec.Decrypt, "encryptor", _Encryptor())

    decrypt.run()

    path_restored = target / "credentials.json"
    assert path_restored.read_json() == {"token": "plaintext"}
    assert not (target / "credentials.json.red.yml").exists()


def test_decrypt_force_overwrites_identical_target(tmp_path, monkeypatch):
    source = sec.Path(tmp_path / "source")
    target = sec.Path(tmp_path / "target")
    path_black = source / "credentials.json.black.yml"
    path_red = target / "credentials.json.red.yml"
    path_black.parent.mkdirf()
    path_red.parent.mkdirf()
    path_black.write_yaml({"token": "ciphertext"})
    path_red.write_yaml({"token": "plaintext"})

    class _Encryptor:
        @staticmethod
        def decrypt(data):
            return {"token": "plaintext"}

    decrypt = sec.Decrypt(source=source, target=target, force=True)
    monkeypatch.setattr(sec.Decrypt, "encryptor", _Encryptor())

    assert decrypt.process_file(path_black) == path_red


def test_decrypt_defaults_source_and_target_to_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    decrypt = sec.Decrypt()

    assert decrypt.source == sec.Path(tmp_path)
    assert decrypt.target == sec.Path(tmp_path)
    assert decrypt.restore is False
    assert decrypt.force is False
    assert decrypt.preserve is False


def test_decrypt_cli_does_not_require_secrets_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    cli = sec.Cli(_cli_parse_args=[
        "decrypt",
        "--source", str(tmp_path / "source"),
        "--target", str(tmp_path / "target"),
    ])

    assert cli.definitions == []
    assert cli.decrypt.source == sec.Path(tmp_path / "source")
    assert cli.decrypt.target == sec.Path(tmp_path / "target")
