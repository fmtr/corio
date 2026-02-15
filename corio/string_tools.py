import re
from collections import namedtuple
from dataclasses import dataclass
from string import Formatter
from textwrap import dedent
from typing import List

from corio.datatype_tools import is_none

ELLIPSIS = '…'
formatter = Formatter()

Segment = namedtuple('Segment', ['literal_text', 'field_name', 'format_spec', 'conversion'])


def parse_string(string: str) -> List[Segment]:
    """

    Return structured version of a string with formatting slots.

    """
    parsed = [Segment(*args) for args in formatter.parse(string)]
    return parsed


def is_format_string(string: str) -> bool:
    """

    Does the string contains string formatting slots (i.e. {})?

    """
    try:
        parsed = parse_string(string)
    except ValueError:
        return False
    if all(datum.field_name is None for datum in parsed):
        return False
    else:
        return True


def get_var_name(string: str) -> str:
    """

    Get the name of a variable from a (resolved) f-string `{a=}`

    """
    name, value = string.split('=', maxsplit=1)
    return name


def format_data(value, **kwargs):
    """

    Format a complex object

    """
    if isinstance(value, str):
        return value.format(**kwargs)
    elif isinstance(value, dict):
        return {format_data(k, **kwargs): format_data(v, **kwargs) for k, v in value.items()}
    elif isinstance(value, list):
        return [format_data(item, **kwargs) for item in value]
    else:
        return value


WHITESPACE = re.compile(r'[\s\-_]+')


def sanitize(*strings, sep: str = '-') -> str:
    """

    Replace spaces with URL- and ID-friendly characters, etc.

    """

    strings = [string for string in strings if string]
    string = ' '.join(strings)
    strings = [c.lower() for c in string if c.isalnum() or c in {' '}]
    string = ''.join(strings)
    string = WHITESPACE.sub(sep, string).strip()

    return string


@dataclass
class Truncation:
    """

    Result type for truncation functions

    """
    text: str
    text_without_sep: str | None
    original: str
    remainder: str | None
    sep: str


def truncate(text, length=None, sep=ELLIPSIS, return_type=str):
    """

    Truncate a string to length characters

    """
    text = flatten(text)
    if len(text) <= length or not length:
        return text if return_type is str else Truncation(text, text, text, None, sep)

    cutoff = length - len(sep)
    truncated = text[:cutoff] + sep

    if return_type is str:
        return truncated
    else:
        return Truncation(
            text=truncated,
            text_without_sep=text[:cutoff],
            original=text,
            remainder=text[cutoff:] or None,
            sep=sep
        )


def truncate_mid(text, length=None, sep=ELLIPSIS, return_type=str):
    """

    Truncate a string to `length` characters in the middle.

    """
    text = flatten(text)
    if len(text) <= length or not length:
        return text if return_type is str else Truncation(text, text, text, '', sep)

    half = (length - len(sep)) // 2
    left = text[:half]
    right = text[-half:]
    truncated = left + sep + right

    if return_type is str:
        return truncated
    else:
        return Truncation(
            text=truncated,
            text_without_sep=None,
            original=text,
            remainder=None,
            sep=sep
        )


def flatten(raw, sep=' '):
    """

    Flatten a multiline string to a single line

    """
    lines = raw.splitlines()
    text = sep.join(lines)
    text = text.strip()
    return text


def join(strings, sep=' '):
    """

    Join a list of strings while removing Nones

    """

    lines = [string for string in strings if not is_none(string) and string != '']
    text = sep.join(str(line) for line in lines)
    return text


def join_natural(items, sep=', ', conj='and'):
    """

    Natural language list

    """

    items = list(items)
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    firsts, last = items[:-1], items[-1]
    firsts_str = join(firsts, sep=sep)
    text = f"{firsts_str} {conj} {last}"
    return text

class Mask:
    """

    Allows partial-like f-strings

    """

    def __init__(self, mask: str):
        self.mask = trim(mask)
        self.mask_data = parse_string(self.mask)
        self.kwargs = {}
        self.args = []

    def format(self, *args, **kwargs):
        """

        If the string is complete, return it, else store field values

        """
        self.args += list(args)
        self.kwargs.update(kwargs)
        try:
            text = self.mask.format(*args, **self.kwargs)
            return text
        except (KeyError, IndexError):
            return self

    def __str__(self):
        """

        Force string output, leaving any unfilled slots as-is.

        """

        fills = {}

        for seg in self.mask_data:
            if seg.field_name:
                fill = self.kwargs.get(seg.field_name, f'{{{seg.field_name}}}')
                fills[seg.field_name] = fill

        return self.mask.format(**fills)

def trim(text: str) -> str:
    """

    Trim strings both horizontally and vertically. Useful when multiline strings are defined in an indented context.

    """
    return dedent(text).strip()


ACRONYM_BOUNDARY = re.compile(r'([A-Z]+)([A-Z][a-z])')
CAMEL_BOUNDARY = re.compile(r'([a-z0-9])([A-Z])')


def camel_to_snake(name: str) -> str:
    """

    Camel case to snake case

    """
    name = ACRONYM_BOUNDARY.sub(r'\1_\2', name)
    name = CAMEL_BOUNDARY.sub(r'\1_\2', name)
    return name.lower()
