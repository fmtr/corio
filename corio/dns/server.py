import asyncio
from dataclasses import dataclass, field
from datetime import timedelta
from functools import cached_property
from typing import Optional

from dns import rcode as dnspython_rcode

from corio import caching as caching
from corio.dns.dm import Exchange, Response
from corio.logs import logger


@dataclass(kw_only=True, eq=False)
class Plain(asyncio.DatagramProtocol):
    """

    Async base class for a plain DNS server using asyncio DatagramProtocol.
    """

    host: str
    port: int
    transport: Optional[asyncio.DatagramTransport] = field(default=None, init=False)
    background_tasks: set[asyncio.Task] = field(default_factory=set, init=False)
    client_name_lookups: dict[str, asyncio.Task] = field(default_factory=dict, init=False)
    started: asyncio.Event = field(default_factory=asyncio.Event, init=False)

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

    @cached_property
    def client_names(self):
        """Cache client IP to reverse-DNS name, including negative results."""
        return caching.TLRU(maxsize=256, ttu_static=timedelta(hours=1), desc='DNS Client Name')

    def connection_made(self, transport: asyncio.DatagramTransport):
        self.transport = transport
        self.started.set()
        logger.info(f'Listening on {self.host}:{self.port}')

    async def wait_started(self):
        await self.started.wait()

    def datagram_received(self, data: bytes, addr):
        ip, port = addr
        exchange = Exchange.from_wire(data, ip=ip, port=port)
        self.create_background_task(self.handle(exchange))

    def create_background_task(self, coroutine) -> asyncio.Task:
        task = asyncio.create_task(coroutine)
        self.background_tasks.add(task)
        task.add_done_callback(self._background_task_done)
        return task

    def _background_task_done(self, task: asyncio.Task):
        self.background_tasks.discard(task)
        if task.cancelled():
            return
        if exception := task.exception():
            logger.exception(str(exception))

    async def wait_for_background_tasks(self):
        """Wait for currently scheduled background work, primarily for shutdown and tests."""
        while self.background_tasks:
            await asyncio.gather(*tuple(self.background_tasks))

    async def start(self):
        """

        Start the async UDP server.
        """

        logger.info(f'Starting async DNS server on {self.host}:{self.port}...')
        await self.loop.create_datagram_endpoint(
            lambda: self,
            local_addr=(self.host, self.port)
        )
        try:
            await asyncio.Future()  # Run until cancelled.
        finally:
            await self.close()

    async def close(self):
        """Stop accepting datagrams and release outstanding async resources."""
        if self.transport is not None:
            self.transport.close()
            self.transport = None
        self.started.clear()

        tasks = tuple(self.background_tasks)
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        client = getattr(self, 'client', None)
        if client is not None and hasattr(client, 'aclose'):
            await client.aclose()

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

        client_name_is_cached = exchange.ip in self.client_names
        if not exchange.is_internal and client_name_is_cached:
            exchange.client_name = self.client_names[exchange.ip]

        with self.get_span(exchange):
            with logger.span(f'Checking cache...'):
                self.check_cache(exchange)

            if not exchange.is_complete:
                try:
                    exchange = await self.resolve(exchange)
                except Exception as exception:
                    response = exchange.request.get_response_template()
                    response.set_rcode(dnspython_rcode.SERVFAIL)
                    exchange.response = Response.from_message(response)
                    exchange.is_complete = True
                    logger.exception(str(exception))
                else:
                    self.cache[exchange.key] = exchange.response

            self.log_dns_errors(exchange)
            self.log_response(exchange)

            if not exchange.is_internal:
                self.transport.sendto(exchange.response.message.to_wire(), exchange.addr)
                if not client_name_is_cached:
                    self.start_client_name_lookup(exchange)

    def start_client_name_lookup(self, exchange: Exchange):
        if exchange.ip in self.client_name_lookups:
            return
        task = self.create_background_task(self.resolve_client_name(exchange))
        self.client_name_lookups[exchange.ip] = task

    async def resolve_client_name(self, exchange: Exchange):
        try:
            reverse = exchange.reverse
            await self.handle(reverse)
            client_name = None
            if reverse.response.answer:
                client_name = reverse.question_last.name.to_text()
            else:
                logger.warning(f'Client name could not be resolved {exchange.ip=}.')
            self.client_names[exchange.ip] = client_name
        except Exception as exception:
            self.client_names[exchange.ip] = None
            logger.exception(str(exception))
        finally:
            self.client_name_lookups.pop(exchange.ip, None)
