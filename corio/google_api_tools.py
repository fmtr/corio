import time
from functools import cached_property

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build, Resource

from corio.logging_tools import logger
from corio.path_tools import Path


class Authenticator:
    """
    Base class for Google API authentication.
    Handles authentication via local token files or interactive OAuth flow.
    """

    PATH: Path | None = None
    SCOPES: list[str] = []
    SERVICE: str | None = None
    VERSION: str | None = None

    def __init__(self):
        """
        Initialize the authenticator and perform initial bootstrap.
        """
        self.boostrap()

    @cached_property
    def name(self) -> str | None:
        """
        The name of the Google service.
        """
        return self.SERVICE

    @cached_property
    def path_token(self) -> Path:
        """
        Path to the JSON file containing the saved authentication token.
        """
        return self.PATH / f'{self.name}.json'

    @cached_property
    def path_code(self) -> Path:
        """
        Path to the file where the authorization code should be written during bootstrap.
        """
        return self.PATH / f'{self.name}.code'

    @cached_property
    def path_creds(self) -> Path:
        """
        Path to the client credentials JSON file.
        """
        return self.PATH / 'credentials.json'

    @property
    def credentials(self) -> Credentials | None:
        """
        Load credentials from the token file and refresh if they are expired.

        Returns:
            The loaded Credentials object, or None if the token file doesn't exist.
        """

        if not self.path_token.exists():
            return None

        data_token = self.path_token.read_json()
        credentials = Credentials.from_authorized_user_info(data_token, self.SCOPES)
        if credentials.expired:
            with logger.span(f'Credentials expired for {self.name}. Will refresh...'):
                logger.warning(f'{self.name}. {self.path_creds.exists()=} {self.path_token.exists()=} {credentials.valid=} {credentials.expired=} {credentials.expiry=}')
                credentials.refresh(Request())
                self.path_token.write_text(credentials.to_json())
        return credentials

    def boostrap(self) -> None:
        """
        Perform initial authentication bootstrap if credentials are not already present.
        Prompts the user to visit an authorization URL and save the resulting code.
        """

        if self.credentials:
            return None

        logger.info(f'Bootstrapping auth for service {self.name} ({self.VERSION})...')

        if self.path_code.exists():
            self.path_code.unlink()

        flow = InstalledAppFlow.from_client_secrets_file(
            self.path_creds,
            self.SCOPES,
            redirect_uri='urn:ietf:wg:oauth:2.0:oob',
        )

        auth_url, _ = flow.authorization_url(
            access_type='offline',
            prompt='consent',
        )

        logger.warning(f'Open this URL for {self.name}')
        print(auth_url)
        logger.warning(f'Then write the returned code into: {self.path_code}')

        while True:
            if self.path_code.exists():
                code = self.path_code.read_text().strip()
                if code:
                    break
            time.sleep(1)

        flow.fetch_token(code=code)
        credentials = flow.credentials
        self.path_token.write_text(credentials.to_json())
        return None

    @cached_property
    def service(self) -> Resource:
        """
        The built Google API service resource.
        """
        return build(self.SERVICE, self.VERSION, credentials=self.credentials)


class AuthenticatorYouTube(Authenticator):
    """

    Base YouTube authenticator

    """

    SCOPES = [
        'https://www.googleapis.com/auth/youtube.force-ssl'
    ]
    SERVICE = 'youtube'
    VERSION = 'v3'


class AuthenticatorGmail(Authenticator):
    """

    Base Gmail authenticator

    """

    SCOPES = [
        'https://www.googleapis.com/auth/gmail.readonly',
        'https://www.googleapis.com/auth/gmail.modify',
        "https://www.googleapis.com/auth/gmail.settings.sharing"
    ]
    SERVICE = 'gmail'
    VERSION = 'v1'
