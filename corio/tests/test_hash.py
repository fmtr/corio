from corio import hash as hash_module


def test_hash_unit_is_stable_and_bounded():
    first = hash_module.hash_unit("corio")
    second = hash_module.hash_unit("corio")

    assert first == second
    assert 0.0 <= first < 1.0


def test_get_hash_readable_length_and_replacements():
    value = hash_module.get_hash_readable("corio", length=16)

    assert len(value) == 16
    assert "O" not in value
    assert "I" not in value
    assert "=" not in value
