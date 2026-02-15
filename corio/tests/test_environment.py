import pytest
from datetime import datetime, date

from fmtr.tools import environment_tools
from fmtr.tools.path_tools import Path
from fmtr.tools.tests import helpers
from fmtr.tools.tools import EMPTY

ENVIRONMENT_TEST_DATA = [
    ('BOOLEAN1', 'Y', environment_tools.get_bool, True),
    ('BOOLEAN2', 'f', environment_tools.get_bool, False),
    ('DATE', '2001-01-01', environment_tools.get_date, date(2001, 1, 1)),
    ('DATETIME', '2021-10-09T10:25:51.425296', environment_tools.get_datetime,
     datetime(2021, 10, 9, 10, 25, 51, 425296)),
    ('INT1', '101', environment_tools.get_int, 101),
    ('INT2', '4.0E+10', environment_tools.get_int, 4.0E+10),
    ('FLOAT1', '123.456', environment_tools.get_float, 123.456),
    ('PATH', '/usr/bin/python', environment_tools.get_path, Path('/usr/bin/python'))
]

ENVIRONMENT_DATA = {key: raw for key, raw, func, expected in ENVIRONMENT_TEST_DATA}


@helpers.parametrize(
    'key,expected',
    ENVIRONMENT_DATA.items()
)
def test_get_env(key, expected):
    """

    """
    with helpers.patch_environment(clear=True, **ENVIRONMENT_DATA):
        actual = environment_tools.get(key)
    assert actual == expected


@helpers.parametrize(
    'expected',
    [None, 101, EMPTY]
)
def test_get_env_missing_raises(expected):
    """

    """
    MISSING_KEY = '!!MISSING!!'
    with helpers.patch_environment(clear=True, **ENVIRONMENT_DATA):
        if expected is EMPTY:
            with pytest.raises(environment_tools.MissingEnvironmentVariable):
                environment_tools.get(MISSING_KEY)
        else:
            actual = environment_tools.get(MISSING_KEY, default=expected)
            assert actual == expected


@helpers.parametrize(
    'key,raw,func,expected',
    ENVIRONMENT_TEST_DATA
)
def test_get_env_type(key, raw, func, expected):
    """

    """
    with helpers.patch_environment(clear=True, **ENVIRONMENT_DATA):
        actual = func(key)
    assert actual == expected


def test_get_env_dict():
    """

    """
    expected = ENVIRONMENT_DATA
    with helpers.patch_environment(clear=True, **ENVIRONMENT_DATA):
        actual = environment_tools.get_dict()
    assert actual == expected
