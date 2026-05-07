import pathlib
import pytest

from corio.hook import MissingExtraError
from corio import path
from corio.tests.helpers import SERIALIZATION_DATA


@pytest.mark.parametrize(
    'args',
    [
        ['/', 'opt', 'data'],
        ['dir', 'data'],
    ]
)
def test_path_args(args):
    expected = str(pathlib.Path(*args))
    actual = str(path.Path(*args))
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
    actual = path.Path.is_abs_win_path(raw)
    assert actual == expected
    actual = path.Path.is_abs_win_path(path.Path(raw, convert_wsl=False))
    assert actual == expected


def test_path_module():
    """



    """
    expected = path.Path(__file__).absolute()
    actual = path.Path.module()
    assert actual == expected


def test_path_package():
    """



    """
    expected = path.Path(__file__).absolute().parent
    actual = path.Path.package()
    assert actual == expected


def test_serialization_json():
    """

    Test round trip for JSON.

    """
    expected = SERIALIZATION_DATA
    path_tmp = path.Path.temp() / 'serialization_test.json'
    path_tmp.write_json(expected)
    actual = path_tmp.read_json()
    path_tmp.unlink()
    assert actual == expected


def test_serialization_yaml():
    """

    Test round trip for YAML, but also add some more complex types as they are supported.

    """
    expected = SERIALIZATION_DATA | {
        'path': path.Path('/usr/bin/a/b/c/d.ini'),
        'bytes': b'test',
        'set': {'foo', 'bar', 'baz'},
        'text': 'Sed ut perspiciatis unde omnis iste natus error sit voluptatem accusantium doloremque laudantium \n' * 100
    }
    path_tmp = path.Path.temp() / 'serialization_test.yaml'
    try:
        path_tmp.write_yaml(expected)
        actual = path_tmp.read_yaml()
    except MissingExtraError:
        pytest.skip("requires yaml extra")
    else:
        path_tmp.unlink()
    assert actual == expected
