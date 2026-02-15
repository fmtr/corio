import pytest

from fmtr.tools import datatype_tools
from fmtr.tools.datatype_tools import TypeConversionFailed
from fmtr.tools.tests import helpers
from fmtr.tools.tools import Raise


@helpers.parametrize(
    'raw, expected',
    [
        ('true', True),
        ('1', True),
        ('t', True),
        ('y', True),
        ('yes', True),
        ('false', False),
        (0, False),
        ('f', False),
        ('n', False),
        ('no', False),
        ('nooo', None),
        ('zzz', None),
        ('zzz', Raise),
    ]
)
def test_to_bool(raw, expected):
    if expected is Raise:
        with pytest.raises(TypeConversionFailed):
            datatype_tools.to_bool(raw, default=Raise)
    else:
        actual = datatype_tools.to_bool(raw)
        assert actual == expected
