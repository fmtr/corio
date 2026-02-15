"""

Tools for handling environment variables etc.

"""
import os
from collections.abc import Callable
from datetime import date, datetime
from fmtr.tools.constants import Constants
from fmtr.tools.datatype_tools import to_bool
from fmtr.tools.path_tools import Path
from fmtr.tools.tools import identity, EMPTY
from typing import Any, Dict


class MissingEnvironmentVariable(KeyError):
    """

    Exception for when a required environment variable is missing.

    """


def get_dict() -> Dict[str, str]:
    """

    Return environment variables as a standard dictionary.

    """
    environment_dict = dict(sorted(dict(os.environ).items()))
    return environment_dict


def get(name: str, default: Any = EMPTY, converter: Callable = identity, convert_empty: bool = False) -> Any:
    """

    Return the specified environment variable, handling default substitution and simple type conversion.

    """
    value = os.getenv(name, default)

    if value is EMPTY:
        msg = f'Environment variable "{name}" is required but has not been set'
        raise MissingEnvironmentVariable(msg)

    if value is not None or convert_empty:
        value = converter(value)

    return value


def get_getter(converter: Callable) -> Callable:
    """

    Return an environment getter for the specified type.

    """

    def func(name: str, default: Any = EMPTY):
        """

        Environment getter that converts to the specified type

        """
        value = get(name, default=default, converter=converter)
        return value

    return func


get_int = get_getter(lambda n: int(float(n)))
get_float = get_getter(float)
get_bool = get_getter(to_bool)
get_date = get_getter(date.fromisoformat)
get_datetime = get_getter(datetime.fromisoformat)
get_path = get_getter(Path)

IS_DEV = get_bool(Constants.FMTR_DEV_KEY, default=False)
CHANNEL = Constants.DEVELOPMENT if IS_DEV else Constants.PRODUCTION
