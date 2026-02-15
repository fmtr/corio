import logging
import os

from corio import environment_tools
from corio.constants import Constants

if environment_tools.IS_DEV:
    STREAM_DEFAULT = ENVIRONMENT_DEFAULT = Constants.DEVELOPMENT
else:
    STREAM_DEFAULT = None
    ENVIRONMENT_DEFAULT = Constants.PRODUCTION

LEVEL_DEFAULT = logging.DEBUG if environment_tools.IS_DEV else logging.INFO

def get_logger(name, version=None, host=Constants.FMTR_OBS_HOST, key=None, org=Constants.ORG_NAME,
               stream=STREAM_DEFAULT, environment=ENVIRONMENT_DEFAULT, level=LEVEL_DEFAULT):
    """

    Get a pre-configured logfire logger, if dependency is present, otherwise default to native logger.

    """

    stream = stream or name

    try:
        import logfire
    except ImportError:
        logger = logging.getLogger(None)
        logger.setLevel(level)
        logger.warning(f'Logging dependencies not installed. Using native logger.')

        return logger

    logger = logfire

    if key is None:
        key = environment_tools.get(Constants.FMTR_OBS_API_KEY_KEY, default=None)

    if key:
        url = f"https://{host}/api/{org}/v1/traces"
        headers = f"Authorization=Basic {key},stream-name={stream}"

        os.environ["OTEL_EXPORTER_OTLP_TRACES_ENDPOINT"] = url
        os.environ["OTEL_EXPORTER_OTLP_HEADERS"] = headers
        os.environ["OTEL_EXPORTER_OTLP_INSECURE"] = str(False).lower()

    if not version:
        from corio.paths import paths
        version = paths.metadata.version

    lev_name_otel = get_otel_level_name(level)

    console_opts = logfire.ConsoleOptions(
        colors='always',
        min_log_level=lev_name_otel,
    )

    logfire.configure(
        service_name=name,
        service_version=version,
        environment=environment,
        send_to_logfire=False,
        console=console_opts,
        scrubbing=logfire.ScrubbingOptions(callback=null_scrubber)
    )

    return logger


def null_scrubber(match):
    """

    Effectively disable scrubbing

    """
    return match.value


def get_current_level(logger):
    """

    Get the current console log level.

    """
    level = logger.DEFAULT_LOGFIRE_INSTANCE.config.console.min_log_level
    return level


def get_logger_names():
    """

    Fetch current native logger names

    """
    return list(logging.getLogger().manager.loggerDict.keys())


OTEL_TO_NATIVE = {
    1: 1,  # trace
    3: 5,  # debug
    5: 10,  # debug (canonical)
    6: 13,  # warn
    8: 17,  # error
    9: 20,  # info
    10: 23,  # notice
    11: 25,  # success/loguru
    13: 30,  # warning
    17: 40,  # error
    21: 50,  # fatal
}


def get_otel_level_name(native_level: int) -> str:
    """

    Convert a native Python logging level number to an OTEL/logfire level name.

    """

    from logfire._internal import constants

    otel_num = constants.LOGGING_TO_OTEL_LEVEL_NUMBERS[native_level]
    name = constants.NUMBER_TO_LEVEL[otel_num]
    return name


def get_native_level_from_otel(otel_name: str) -> int:
    """

    Convert an OTEL/logfire level name to a native Python logging level number.

    """
    from logfire._internal import constants

    otel_num = constants.LEVEL_NUMBERS[otel_name]
    level = OTEL_TO_NATIVE[otel_num]
    return level


logger = get_logger(name=Constants.LIBRARY_NAME)

if __name__ == '__main__':
    logger.info('Hello World')
    logger.warning('test warning')
    logger.debug('Hello World')
    logger
