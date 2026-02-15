import json
import json_repair

from fmtr.tools.logging_tools import logger
from fmtr.tools.tools import Raise


def from_json(json_string, default=None):
    """

    Error-tolerant JSON deserialization

    """
    try:
        return json_repair.loads(json_string)
    except json.JSONDecodeError as exception:
        if default is Raise:
            raise exception
        logger.warning(f'Deserialization failed {repr(exception)}: {json_string}')
        return default
