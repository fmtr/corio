from dataclasses import dataclass

from fmtr.tools.dns_tools import server, client
from fmtr.tools.dns_tools.dm import Exchange
from fmtr.tools.logging_tools import logger


@dataclass(kw_only=True, eq=False)
class Proxy(server.Plain):
    """

    Base for a DNS Proxy server (plain server) TODO: Allow subclassing of any server type.

    """

    client: client.HTTP

    def process_question(self, exchange: Exchange):
        """

        Modify exchange based on initial question.

        """
        return

    def process_upstream(self, exchange: Exchange):
        """

        Modify exchange after upstream response.

        """
        return

    def finalize(self, exchange: Exchange):
        """

        Finalize a still open exchange.

        """
        exchange.is_complete = True

    async def resolve(self, exchange: Exchange) -> Exchange:
        """

        Resolve a request, processing each stage, initial question, upstream response etc.
        Subclasses can override the relevant processing methods to implement custom behaviour.

        """
        with logger.span(f'Processing question...'):
            self.process_question(exchange)
        if exchange.is_complete:
            return exchange

        with logger.span(f'Making upstream request...'):
            self.client.resolve(exchange)
        if exchange.is_complete:
            return exchange

        with logger.span(f'Processing upstream response...'):
            self.process_upstream(exchange)
        if exchange.is_complete:
            return exchange

        self.finalize(exchange)

        return exchange
