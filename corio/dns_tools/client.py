from dataclasses import dataclass
from dns import query as dnspython_query, message as dnspython_message, rdatatype as dnspython_rdatatype, rcode as dnspython_rcode
from fmtr.tools import http_tools as http
from fmtr.tools.dns_tools.dm import Exchange, Response
from fmtr.tools.logging_tools import logger
from functools import cached_property
from httpx_retries import Retry, RetryTransport
from typing import Optional

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


class HTTPClientDoH(http.Client):
    """

    Base HTTP client for DoH-appropriate retry strategy.

    """
    TRANSPORT = RetryTransport(retry=RETRY_STRATEGY)


@dataclass
class Plain:
    """

    Plain DNS

    """
    host: str
    port: int = 53
    ttl_min: Optional[int] = None

    def resolve(self, exchange: Exchange):

        with logger.span(f'UDP {self.host}:{self.port}'):
            response_plain = dnspython_query.udp(q=exchange.query_last, where=self.host, port=self.port)
            response = Response.from_message(response_plain)
            for answer in response.message.answer:
                answer.ttl = max(answer.ttl, self.ttl_min or answer.ttl)

        exchange.response = response


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


    @cached_property
    def ip(self):
        message = dnspython_message.make_query(self.host, dnspython_rdatatype.A, flags=0)
        exchange = Exchange.from_wire(message.to_wire(), ip=None, port=None)
        self.BOOTSTRAP.resolve(exchange)
        ip = next(iter(exchange.response.answer.items.keys())).address
        return ip

    def resolve(self, exchange: Exchange):
        """

        Resolve via DoH

        """

        headers = self.HEADERS | dict(Host=self.host)
        url = self.url.format(host=self.ip)

        try:
            response_doh = self.CLIENT.post(url, headers=headers, content=exchange.query_last.to_wire())
            response_doh.raise_for_status()
            response = Response.from_http(response_doh)
            exchange.response = response

        except Exception as exception:
            exchange.response.message.set_rcode(dnspython_rcode.SERVFAIL)
            exchange.response.is_complete = True
            logger.exception(exception)
