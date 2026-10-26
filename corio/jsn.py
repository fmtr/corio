import dataclasses
import json
from datetime import date, datetime, time
from pathlib import Path

from corio.constants import Constants


def _default(obj):
    if dataclasses.is_dataclass(obj):
        return dataclasses.asdict(obj)

    if isinstance(obj, (date, datetime, time)):
        return obj.isoformat()

    if isinstance(obj, Path):
        return str(obj)

    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


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
