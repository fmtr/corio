from pyrage import x25519

from corio.encrypt import Encryptor, EncryptorValues


def test_encryptor_round_trip():
    identity = x25519.Identity.generate()
    encryptor = Encryptor(key=str(identity))
    expected = {
        "service": "corio",
        "enabled": True,
        "retries": 3,
        "tags": ["alpha", "beta"],
        "metadata": {"region": "eu-west-2"},
    }

    encrypted = encryptor.encrypt(expected)
    assert isinstance(encrypted, str)
    assert encryptor.is_encrypted(encrypted)

    actual = encryptor.decrypt(encrypted)
    assert actual == expected


def test_encryptor_values_round_trip():
    identity = x25519.Identity.generate()
    encryptor = EncryptorValues(key=str(identity))
    expected = {
        "api": {
            "token": "test-token",
            "enabled": True,
            "ports": [80, 443],
        },
        "count": 2,
    }

    encrypted = encryptor.encrypt(expected)
    assert encrypted != expected
    assert encryptor.is_encrypted(encrypted["api"]["token"])
    assert encryptor.is_encrypted(encrypted["api"]["ports"][0])

    actual = encryptor.decrypt(encrypted)
    assert actual == expected
