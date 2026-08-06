from functools import cached_property

import httpx
from httpx_retries import RetryTransport, Retry

from corio import logs

logs.logger.instrument_httpx()


class ClientBase:
    """Shared defaults for synchronous and asynchronous HTTP clients."""

    TIMEOUT = 10

    def __init__(self, *args, **kwargs):
        super().__init__(*args, transport=self.transport, timeout=self.TIMEOUT, **kwargs)

    @cached_property
    def transport(self) -> RetryTransport:
        """

        Default Transport with retry

        """
        return RetryTransport(
            retry=self.retry
        )

    @cached_property
    def retry(self) -> Retry:
        """

        Default Retry

        """
        return Retry(
            allowed_methods=Retry.RETRYABLE_METHODS,
            backoff_factor=1.0
        )


class Client(ClientBase, httpx.Client):
    """Instrumented synchronous HTTP client."""


class AsyncClient(ClientBase, httpx.AsyncClient):
    """Instrumented asynchronous HTTP client."""


client = Client()
