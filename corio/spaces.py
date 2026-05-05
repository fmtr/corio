import importlib
import logging
import subprocess
import sys

from corio import netrc
from corio.env import get

VARS = [
    (FMTR_LOG_LEVEL := 'FMTR_LOG_LEVEL'),
    (PACKAGE_NAME := 'PACKAGE_NAME'),
    (PYPI_HOST := 'PYPI_HOST'),
    (PYPI_USERNAME := 'PYPI_USERNAME'),
    (PYPI_PASSWORD := 'PYPI_PASSWORD'),
]


def run():
    FMTR_LOG_LEVEL = get('FMTR_LOG_LEVEL', default='INFO')
    logging.getLogger().setLevel(FMTR_LOG_LEVEL)

    vars = {key: get(key) for key in VARS}

    with netrc.get() as netrc_obj:
        netrc_obj[vars[PYPI_HOST]] = {
            netrc.LOGIN: vars[PYPI_USERNAME],
            netrc.PASSWORD: vars[PYPI_PASSWORD]
        }

    command = [
        sys.executable,
        '-m',
        'pip',
        'install',
        vars[PACKAGE_NAME],
        '--no-input',
        '--index-url',
        f'https://{vars[PYPI_HOST]}'
    ]

    print(f'Starting {vars[PACKAGE_NAME]}...')

    subprocess.run(command, check=True)

    interface = importlib.import_module(f'{vars[PACKAGE_NAME]}.interface')
    interface.run()
