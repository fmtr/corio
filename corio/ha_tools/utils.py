import os
from dotenv import load_dotenv

from fmtr.tools.ha_tools import constants
from fmtr.tools.logging_tools import logger
from fmtr.tools.string_tools import ELLIPSIS


def apply_addon_env():
    """

    If we're inside an addon container, we need to source its environment file and convert its options.json to environment variables.

    """
    path = constants.PATH_ADDON_ENV
    if path.exists():
        logger.warning(f'Loading addon environment from "{path}"...')
        load_dotenv(path)

    for key, value in convert_options_data().items():
        os.environ[key] = value


def convert_options_data() -> dict[str, str]:
    """

    Convert Home Assistant addon options.json to an environment-ready dict.

    """
    path = constants.PATH_ADDON_OPTIONS

    data_env = {}

    if not path.exists():
        return data_env

    data_json = path.read_json()

    with logger.span(f'Converting addon "{path}" to environment variables...'):
        for key, value in data_json.items():
            key_env = key.upper()
            val_env = str(value)
            logger.debug(f'Converting {key_env}={ELLIPSIS}" to environment variable...')
            data_env[key_env] = val_env

    return data_env
