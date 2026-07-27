import json
from datetime import date, datetime, time

from corio.constants import Constants


def _default(obj):
    return obj.isoformat()


def to_json(obj):
    """

    Serialise to JSON

    """
    json_str = json.dumps(
        obj,
        indent=Constants.SERIALIZATION_INDENT,
        ensure_ascii=False,
        default=_default,
    )
    return json_str


def from_json(json_str: str):
    """

    Deserialise from JSON

    """
    obj = json.loads(json_str)
    return obj
