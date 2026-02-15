import pathlib

import pytest

from fmtr.tools import path_tools
from fmtr.tools.tests.helpers import SERIALIZATION_DATA


@pytest.mark.parametrize(
    'args',
    [
        ['/', 'opt', 'data'],
        ['dir', 'data'],
    ]
)
def test_path_args(args):
    expected = str(pathlib.Path(*args))
    actual = str(path_tools.Path(*args))
    assert actual == expected


@pytest.mark.parametrize(
    'raw, expected',
    [
        (r'C:\test', True),
        (r'd:\test', True),
        (r'u:', True),
        (r'x:\test\file.exe', True),
        (r'\\wsl.localhost\shell\bin', True),
        (r'/opt/data', False),
        (r'/bin/usr/python', False),
        (r'test/path', False),
        (r'test\path', False),
    ]
)
def test_path_is_abs_win_path(raw, expected):
    actual = path_tools.Path.is_abs_win_path(raw)
    assert actual == expected
    actual = path_tools.Path.is_abs_win_path(path_tools.Path(raw, convert_wsl=False))
    assert actual == expected


def test_path_module():
    """



    """
    expected = path_tools.Path(__file__).absolute()
    actual = path_tools.Path.module()
    assert actual == expected


def test_path_package():
    """



    """
    expected = path_tools.Path(__file__).absolute().parent
    actual = path_tools.Path.package()
    assert actual == expected


def test_serialization_json():
    """

    Test round trip for JSON.

    """
    expected = SERIALIZATION_DATA
    path = path_tools.Path.temp() / 'serialization_test.json'
    path.write_json(expected)
    actual = path.read_json()
    path.unlink()
    assert actual == expected


def test_serialization_yaml():
    """

    Test round trip for YAML, but also add some more complex types as they are supported.

    """
    expected = SERIALIZATION_DATA | {
        'path': path_tools.Path('/usr/bin/a/b/c/d.ini'),
        'bytes': b'test',
        'set': {'foo', 'bar', 'baz'},
        'text': 'Sed ut perspiciatis unde omnis iste natus error sit voluptatem accusantium doloremque laudantium \n' * 100
    }
    path = path_tools.Path.temp() / 'serialization_test.yaml'
    path.write_yaml(expected)
    actual = path.read_yaml()
    path.unlink()
    assert actual == expected
