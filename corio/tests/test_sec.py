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

    assert (target / "a" / "b" / ".env").read_data() == {"API_KEY": "plaintext"}


def test_decrypt_defaults_source_and_target_to_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    decrypt = sec.Decrypt()

    assert decrypt.source == sec.Path(tmp_path)
    assert decrypt.target == sec.Path(tmp_path)


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
