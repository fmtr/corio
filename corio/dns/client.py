import asyncio
from dataclasses import dataclass, field
from functools import cached_property
from typing import Optional, Dict

from dns import asyncquery as dnspython_asyncquery, message as dnspython_message, rdatatype as dnspython_rdatatype, \
    rcode as dnspython_rcode
from httpx_retries import Retry

from corio import https as https
from corio.dns.dm import Exchange, Response
from corio.logs import logger

RETRY_STRATEGY = Retry(
    total=2,  # initial + 1 retry
    allowed_methods={"GET", "POST"},
    status_forcelist={502, 503, 504},
    retry_on_exceptions=None,  # defaults to httpx.TransportError etc.
    backoff_factor=0.25,  # short backoff (e.g. 0.25s, 0.5s)
    max_backoff_wait=0.75,  # max total delay before giving up
    backoff_jitter=0.1,  # small jitter to avoid retry bursts
    respect_retry_after_header=False,  # DoH resolvers probably won't set this
)


class HTTPClientDoH(https.AsyncClient):
    """

    Base HTTP client for DoH-appropriate retry strategy.

    """

    @cached_property
    def retry(self) -> Retry:
        return RETRY_STRATEGY


@dataclass
class Plain:
    """

    Plain DNS

    """
    host: str
    port: int = 53
    timeout: float = 2.0
    ttl_min: Optional[int] = None
    ttl_defaults: Dict[str, int] | None = None

    async def resolve(self, exchange: Exchange):

        with logger.span(f'UDP {self.host}:{self.port}'):
            response_plain = await dnspython_asyncquery.udp(
                q=exchange.query_last,
                where=self.host,
                port=self.port,
                timeout=self.timeout,
            )
            response = Response.from_message(response_plain, ttl_defaults=self.ttl_defaults)
            for answer in response.message.answer:
                answer.ttl = max(answer.ttl, self.ttl_min or answer.ttl)

        exchange.response = response

    async def aclose(self):
        pass


@dataclass
class HTTP:
    """

    DNS over HTTP

    """

    HEADERS = {"Content-Type": "application/dns-message"}
    CLIENT = HTTPClientDoH()
    BOOTSTRAP = Plain('8.8.8.8')

    host: str
    url: str
    timeout: float = 3.0
    _ip: Optional[str] = field(default=None, init=False, repr=False)

    async def get_ip(self) -> str:
        if self._ip is not None:
            return self._ip

        message = dnspython_message.make_query(self.host, dnspython_rdatatype.A, flags=0)
        exchange = Exchange.from_wire(message.to_wire(), ip=None, port=None)
        await self.BOOTSTRAP.resolve(exchange)
        self._ip = next(iter(exchange.response.answer.items.keys())).address
        return self._ip

    async def resolve(self, exchange: Exchange):
        """

        Resolve via DoH

        """

        try:
            async with asyncio.timeout(self.timeout):
                headers = self.HEADERS | dict(Host=self.host)
                url = self.url.format(host=await self.get_ip())
                response_doh = await self.CLIENT.post(url, headers=headers, content=exchange.query_last.to_wire())
                response_doh.raise_for_status()
                response = Response.from_http(response_doh)
                exchange.response = response

        except Exception as exception:
            exchange.response.message.set_rcode(dnspython_rcode.SERVFAIL)
            exchange.is_complete = True
            logger.exception(str(exception))

    async def aclose(self):
        await self.CLIENT.aclose()
