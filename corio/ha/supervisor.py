import aiohasupervisor

from corio import env as env
from corio.ha import constants


class Client(aiohasupervisor.SupervisorClient):
    """

    Client stub

    """

    def __init__(self, *args, api_url: str = constants.URL_SUPERVISOR_ADDON, token: str, **kwargs):
        token = token or env.get(constants.SUPERVISOR_TOKEN_KEY)
        super().__init__(*args, api_host=api_url, token=token, **kwargs)
