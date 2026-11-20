from corio import datatype
from corio.tests import helpers


@helpers.parametrize(
    'raw, expected',
    [
        ('true', True),
        ('1', True),
        ('y', True),
        ('yes', True),
        ('on', True),
        ('false', False),
        (0, False),
        ('f', False),
        ('n', False),
        ('no', False),
        ('nooo', False),
        ('zzz', False),
    ]
)
def test_to_bool(raw, expected):
    actual = datatype.to_bool(raw)
    assert actual == expected
