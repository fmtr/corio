import base64
import hashlib
from zlib import crc32

from corio.constants import Constants

SPECIALS = {'O': '9', '=': '9', 'I': '9'}

def hash_unit(value: str) -> float:
    """

    Hash the input string to a value between 0.0 and 1.0 (not secure).

    """
    value = str(value).encode(Constants.ENCODING)
    return float(crc32(value) & 0xffffffff) / 2 ** 32


def get_hash_readable(string, length=None):
    """

    Get hash optimised for information density and readability.

    """
    hash_sha1 = hashlib.sha1(string.encode()).digest()
    hash_b32 = base64.b32encode(hash_sha1).decode()
    value = hash_b32[:length]
    for old, new in SPECIALS.items():
        value = value.replace(old, new)
    return value
