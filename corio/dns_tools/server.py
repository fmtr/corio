import asyncio
from dataclasses import dataclass, field
from datetime import timedelta
from dns import rcode as dnspython_rcode
from fmtr.tools import caching_tools as caching
from fmtr.tools.dns_tools.dm import Exchange
from fmtr.tools.logging_tools import logger
from functools import cached_property
from typing import Optional


@dataclass(kw_only=True, eq=False)
class Plain(asyncio.DatagramProtocol):
    """

    Async base class for a plain DNS server using asyncio DatagramProtocol.
    """

    host: str
    port: int
    transport: Optional[asyncio.DatagramTransport] = field(default=None, init=False)

    @cached_property
    def loop(self):
        return asyncio.get_event_loop()


    @cached_property
    def cache(self):
        """

        Overridable cache.
        """
        cache = caching.TLRU(maxsize=1_024, ttu_static=timedelta(hours=1), desc='DNS Request')
        return cache

    def connection_made(self, transport: asyncio.DatagramTransport):
        self.transport = transport
        logger.info(f'Listening on {self.host}:{self.port}')

    def datagram_received(self, data: bytes, addr):
        ip, port = addr
        exchange = Exchange.from_wire(data, ip=ip, port=port)
        asyncio.create_task(self.handle(exchange))

    async def start(self):
        """

        Start the async UDP server.
        """

        logger.info(f'Starting async DNS server on {self.host}:{self.port}...')
        await self.loop.create_datagram_endpoint(
            lambda: self,
            local_addr=(self.host, self.port)
        )
        await asyncio.Future()  # Prevent exit by blocking forever

    async def resolve(self, exchange: Exchange) -> Exchange:
        """

        To be defined in subclasses.

        """
        raise NotImplementedError

    def check_cache(self, exchange: Exchange):
        if exchange.key in self.cache:
            logger.info(f'Request found in cache.')
            exchange.response = self.cache[exchange.key]
            exchange.response.message.id = exchange.request.message.id
            exchange.is_complete = True

    def get_span(self, exchange: Exchange):
        """

        Get handling span

        """
        request = exchange.request
        span = logger.span(
            f'Handling request {exchange.client_name=} {request.message.id=} {request.type_text} {request.name_text} {request.question=}...'
        )
        return span

    def log_response(self, exchange: Exchange):
        """

        Log when resolution complete

        """
        request = exchange.request
        response = exchange.response
        logger.info(
            f'Resolution complete {exchange.client_name=} {request.message.id=} {request.type_text} {request.name_text} {request.question=} {exchange.is_complete=} {response.rcode=} {response.rcode_text=} {response.answer=} {response.blocked_by=}...'
        )

    def log_dns_errors(self, exchange: Exchange):
        """

        Warn about any errors

        """
        if exchange.response.rcode != dnspython_rcode.NOERROR:
            logger.warning(f'Error {exchange.response.rcode_text=}')

    async def handle(self, exchange: Exchange):
        """

        Warn about any errors

        """
        if not exchange.request.is_valid:
            raise ValueError(f'Only one question per request is supported. Got {len(exchange.request.question)} questions.')

        if not exchange.is_internal:
            await self.handle(exchange.reverse)
            client_name = exchange.reverse.question_last.name.to_text()
            if not exchange.reverse.response.answer:
                logger.warning(f'Client name could not be resolved {client_name=}.')
            exchange.client_name = client_name

        with self.get_span(exchange):
            with logger.span(f'Checking cache...'):
                self.check_cache(exchange)

            if not exchange.is_complete:
                exchange = await self.resolve(exchange)
                self.cache[exchange.key] = exchange.response

            self.log_dns_errors(exchange)
            self.log_response(exchange)

        if exchange.is_internal:
            return

        self.transport.sendto(exchange.response.message.to_wire(), exchange.addr)
