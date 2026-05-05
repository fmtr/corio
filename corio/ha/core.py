import homeassistant_api

from corio import env as env
from corio.ha import constants


class Client(homeassistant_api.Client):
    """

    Client stub

    """

    def __init__(self, *args, api_url: str = constants.URL_CORE_ADDON, token: str, **kwargs):
        token = token or env.get(constants.SUPERVISOR_TOKEN_KEY)
        super().__init__(*args, api_url=api_url, token=token, **kwargs)
