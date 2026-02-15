from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from corio.logging_tools import logger


class Authenticator:
    """

    Authenticate via link or saved token

    """

    PATH = None
    SCOPES = []
    SERVICE = None
    VERSION = None
    PORT = 0

    @classmethod
    def auth(cls):
        """

        Do initial authentication or refresh token if expired.

        """
        logger.info(f'Doing auth for service {cls.SERVICE} ({cls.VERSION})...')

        PATH_CREDS = cls.PATH / 'credentials.json'
        PATH_TOKEN = cls.PATH / f'{cls.SERVICE}.json'

        if PATH_TOKEN.exists():
            data_token = PATH_TOKEN.read_json()
            credentials = Credentials.from_authorized_user_info(data_token, cls.SCOPES)
            if credentials.expired:
                with logger.span(f'Credentials expired for {cls.SERVICE}. Will refresh...'):
                    logger.warning(f'{cls.SERVICE}. {PATH_CREDS.exists()=} {PATH_TOKEN.exists()=} {credentials.valid=} {credentials.expired=} {credentials.expiry=}')
                    credentials.refresh(Request())
                    PATH_TOKEN.write_text(credentials.to_json())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(PATH_CREDS, cls.SCOPES)
            flow.authorization_url(prompt='consent', access_type='offline')
            credentials = flow.run_local_server(open_browser=False, port=cls.PORT)
            PATH_TOKEN.write_text(credentials.to_json())

        return build(cls.SERVICE, cls.VERSION, credentials=credentials)
