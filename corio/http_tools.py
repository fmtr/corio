import httpx
from fmtr.tools import logging_tools
from functools import cached_property
from httpx_retries import RetryTransport, Retry

logging_tools.logger.instrument_httpx()


class Client(httpx.Client):
    """

    Instrumented client base

    """

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


client = Client()

if __name__ == '__main__':
    resp = client.get('https://postman-echo.com/delay/5')
    resp.raise_for_status()
    print(resp.json())
    resp
