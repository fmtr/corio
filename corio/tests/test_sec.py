from corio import sec


def test_env_decrypt_writes_into_run_secrets_and_chowns_recursively(tmp_path, monkeypatch):
    path_black = sec.Path(tmp_path / ".env.black.yml")
    path_black.write_yaml({"API_KEY": "ciphertext"})

    env = sec.Env(
        name="dns",
        black=path_black,
        user="foo",
    )

    monkeypatch.setattr(sec.Env, "SECRET_ROOT", sec.Path(tmp_path / "run" / "secrets"))

    class _Encryptor:
        @staticmethod
        def decrypt(data):
            return {"API_KEY": "plaintext"}

    monkeypatch.setattr(sec.Env, "encryptor", _Encryptor())

    chown_calls = []

    def _chown(self, user, recurse=False):
        chown_calls.append((self, user, recurse))

    monkeypatch.setattr(sec.Path, "chown", _chown)

    env.run()

    path_secret = sec.Path(tmp_path / "run" / "secrets" / "dns")
    path_red = path_secret / ".env"

    assert path_secret.is_dir()
    assert path_red.read_data() == {"API_KEY": "plaintext"}
    assert chown_calls == [(path_secret, "foo", True)]
