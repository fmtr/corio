from datetime import timezone

from corio import dt


def test_now_is_utc_and_in_bounds():
    value = dt.now()

    assert value.tzinfo == timezone.utc
    assert dt.MIN <= value <= dt.MAX
