# `from corio import encrypt`

`encrypt` provides AGE-based encryption helpers for serializable Python data.

Classes:

- `Encryptor`: encrypt/decrypt full payloads
- `EncryptorValues`: tree transform that encrypts/decrypts leaf values
- `EncryptorValuesSelect`: selective node encryption using path-match patterns

Install:

```bash
pip install "corio[encrypt]" --upgrade
```

## Behavior

- Values are serialized to JSON before encryption.
- Cipher payloads are wrapped in a recognizable header marker.
- `EncryptorValues*` preserves tree structure and only transforms leaves.

## Example: Selective Node Encryption

```python
from corio import encrypt

data = {
    "service": {"token": "abc", "region": "eu"},
    "db": {"password": "secret", "port": 5432},
}

enc = encrypt.EncryptorValuesSelect(nodes=["service/token", "db/password"])
cipher = enc.encrypt(data)
plain = enc.decrypt(cipher)
```

`nodes` accepts path-style match expressions evaluated against leaf nodes.

By default the key is read from the `FMTR_AGE_KEY` environment variable.

