import random

import pytest

from corio import rand


def test_temporary_seed_is_deterministic():
    with rand.temporary_seed(7):
        first = random.random()

    with rand.temporary_seed(7):
        second = random.random()

    assert first == second


def test_weighted_choices_helpers():
    with rand.temporary_seed(0):
        values = rand.choices_w(("a", 1), ("b", 9), k=20)
        single = rand.choice_w(("a", 1), ("b", 9))

    assert set(values).issubset({"a", "b"})
    assert single in {"a", "b"}


def test_prob_uses_threshold(monkeypatch):
    monkeypatch.setattr(rand.random, "random", lambda: 0.2)
    assert rand.prob(0.3) is True
    assert rand.prob(0.1) is False


def test_rand_log10_bounds_and_errors():
    assert rand.rand_log10(5, 5) == 5

    with rand.temporary_seed(2):
        value = rand.rand_log10(1, 1000)
    assert 1 <= value <= 1000

    with rand.temporary_seed(2):
        value_int = rand.rand_log10(1, 100)
    assert isinstance(value_int, int)
    assert 1 <= value_int <= 100

    with pytest.raises(ValueError):
        rand.rand_log10(-1, 10)
