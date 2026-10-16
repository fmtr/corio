import hashlib
import pytest
from pyrage import x25519

from corio import encrypt
from corio.encrypt import Encryptor, EncryptorValues, EncryptorValuesSelect, Node
from corio.path import Path


@pytest.fixture
def key():
    return str(x25519.Identity.generate())


@pytest.fixture(autouse=True)
def deterministic_age(monkeypatch):
    encrypted_values = {}

    def fake_encrypt(plain_bytes, recipients):
        ciphertext = hashlib.sha256(plain_bytes).digest()
        encrypted_values[ciphertext] = plain_bytes
        return ciphertext

    def fake_decrypt(ciphertext, identities):
        return encrypted_values[ciphertext]

    monkeypatch.setattr(encrypt.pyrage, "encrypt", fake_encrypt)
    monkeypatch.setattr(encrypt.pyrage, "decrypt", fake_decrypt)


def test_encryptor_round_trip(key):
    encryptor = Encryptor(key=key)
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


def test_encryptor_values_round_trip(key):
    encryptor = EncryptorValues(key=key)
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


def test_encryptor_values_select_encrypts_each_capture_group(key):
    encryptor = EncryptorValuesSelect(
        key=key,
        nodes=[Node(glob="app/*/password", pattern=r"https?://user:(.*)@.*&token=(.*)")],
    )
    expected = {
        "app": {
            "credentials": {
                "password": "https://user:alice@example.test&token=secret",
            },
            "other": "not encrypted",
        }
    }

    encrypted = encryptor.encrypt(expected)
    assert encrypted == {
        "app": {
            "credentials": {
                "password": "https://user:⁂ClBQCyo0Nf50cod+si1I1HoijpRrC5kat0AqjQD2sy0=⁂@example.test&token=⁂wZgCZPwiOokK+ug8kb0tQ47yrQ2udR/eo2YMPlVrE5Y=⁂",
            },
            "other": "not encrypted",
        }
    }
    assert encryptor.decrypt(encrypted) == expected


def test_encryptor_values_select_encrypts_partial_root_scalar(key):
    encryptor = EncryptorValuesSelect(
        key=key,
        nodes=[Node(glob=None, pattern=r"user=(.*);token=(.*)")],
    )
    expected = "user=alice;token=secret"

    encrypted = encryptor.encrypt(expected)

    assert encrypted == "user=⁂ClBQCyo0Nf50cod+si1I1HoijpRrC5kat0AqjQD2sy0=⁂;token=⁂wZgCZPwiOokK+ug8kb0tQ47yrQ2udR/eo2YMPlVrE5Y=⁂"
    assert encryptor.decrypt(encrypted) == expected


def test_encryptor_values_select_finds_root_node_among_other_nodes(key):
    encryptor = EncryptorValuesSelect(
        key=key,
        nodes=[
            Node(glob="app/*", pattern=r"user=(.*);token=(.*)"),
            Node(glob=None, pattern=r"user=(.*);token=(.*)"),
        ],
    )

    encrypted = encryptor.encrypt("user=alice;token=secret")

    assert encryptor.is_encrypted(encrypted)


def test_encryptor_values_select_can_partially_encrypt_a_root_scalar(key):
    encryptor = EncryptorValuesSelect(
        key=key,
        nodes=[Node(glob=None, pattern=r"user=(.*);token=(.*)")],
    )

    encrypted = encryptor.encrypt("user=alice;token=secret")

    assert encryptor.is_encrypted(encrypted)
    assert encryptor.decrypt(encrypted) == "user=alice;token=secret"


def test_encryptor_values_select_does_not_apply_non_root_node_to_root_scalar(key):
    encryptor = EncryptorValuesSelect(
        key=key,
        nodes=[Node(glob="app/*", pattern=r"user=(.*);token=(.*)")],
    )

    value = "user=alice;token=secret"

    assert encryptor.encrypt(value) == value


def test_encryptor_values_select_can_leave_a_root_scalar_unencrypted(key):
    encryptor = EncryptorValuesSelect(
        key=key,
        nodes=[Node(glob=None, pattern=False)],
    )

    value = "user=alice;token=secret"

    assert encryptor.encrypt(value) == value


def test_encryptor_values_select_reports_an_unmatched_partial_pattern(key):
    encryptor = EncryptorValuesSelect(
        key=key,
        nodes=[Node(glob="app/*", pattern=r"user=(.*);token=(.*)")],
    )

    with pytest.raises(ValueError, match="app/secret"):
        encryptor.encrypt({"app": {"secret": "not a user token"}})


@pytest.mark.parametrize(
    ("pattern", "value", "capture_count"),
    [
        (r"postgres://([^:]+):(.*)@([^/]+)/(.+)", "postgres://alice:secret@db.example/app", 4),
        (r"Bearer (.*) \((.*)\)", "Bearer access-token (refresh-token)", 2),
        (r"host=(.*);port=(\d+);database=(.*)", "host=db.example;port=5432;database=app", 3),
    ],
)
def test_encryptor_values_select_supports_common_partial_secret_formats(
        key, pattern, value, capture_count
):
    encryptor = EncryptorValuesSelect(
        key=key,
        nodes=[Node(glob="*/secret", pattern=pattern)],
    )

    encrypted = encryptor.encrypt({"app": {"secret": value}})["app"]["secret"]

    assert encrypted.count(encryptor.LEFT) == capture_count * 2
    assert encryptor.decrypt({"app": {"secret": encrypted}}) == {"app": {"secret": value}}


def test_encryptor_header_matches_multiple_fragments(key):
    encryptor = Encryptor(key=key)
    first = encryptor.encrypt("one")
    second = encryptor.encrypt("two")

    value = f"before {first} between {second} after"
    assert encryptor.is_encrypted(value)
    assert encryptor.decrypt(value) == "before one between two after"


def test_encryptor_values_select_root_encryption_can_be_disabled_with_none():
    encryptor = EncryptorValuesSelect.__new__(EncryptorValuesSelect)

    encryptor.nodes = []
    assert encryptor.include(Path())

    encryptor.nodes = None
    assert not encryptor.include(Path())
