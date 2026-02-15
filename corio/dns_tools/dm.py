import dns
import httpx
from dataclasses import dataclass, field
from dns import rcode as dnspython_rcode, reversename as dnspython_reversename
from dns.message import Message, QueryMessage
from dns.rrset import RRset
from functools import cached_property
from typing import Self, Optional, List

from corio.string_tools import join

TTL_CODE_DEFAULTS = {
    dnspython_rcode.NOERROR: 300,  # Successful query
    dnspython_rcode.FORMERR: 60,  # Format error
    dnspython_rcode.SERVFAIL: 10,  # Server failure
    dnspython_rcode.NXDOMAIN: 60 * 60,  # Non-existent domain
    dnspython_rcode.NOTIMP: 60,  # Not implemented
    dnspython_rcode.REFUSED: 60,  # Refused
    dnspython_rcode.YXDOMAIN: 600,  # Name exists when it should not
    dnspython_rcode.YXRRSET: 600,  # RR Set exists when it should not
    dnspython_rcode.NXRRSET: 300,  # RR Set that should exist does not
    dnspython_rcode.NOTAUTH: 60,  # Not authorized
    dnspython_rcode.NOTZONE: 60  # Name not contained in zone
}

@dataclass
class BaseDNSData:
    """

    DNS response object.

    """
    wire: bytes

    @cached_property
    def message(self) -> Message:
        return dns.message.from_wire(self.wire)

    @classmethod
    def from_message(cls, message: Message) -> Self:
        return cls(message.to_wire())

@dataclass
class Response(BaseDNSData):
    """

    DNS response object.

    """

    http: Optional[httpx.Response] = None
    blocked_by: Optional[str] = None

    @classmethod
    def from_http(cls, response: httpx.Response) -> Self:
        """

        Initialise from an HTTP response.

        """
        self = cls(response.content, http=response)
        return self

    @property
    def answer(self) -> Optional[RRset]:
        """

        Get the latest answer, if one exists.

        """
        if not self.message.answer:
            return None
        return self.message.answer[-1]

    @property
    def rcode(self) -> dnspython_rcode.Rcode:
        return self.message.rcode()

    @property
    def rcode_text(self) -> str:
        return dnspython_rcode.to_text(self.rcode)

    @property
    def ttl(self) -> int:
        """

        Get median TTL from answers, falling back to authority, then to error-code defaults.

        """
        answers = self.message.answer or self.message.authority
        if answers:
            ttls = [answer.ttl for answer in answers]
            ttl = min(ttls)
            return ttl

        ttl = TTL_CODE_DEFAULTS.get(self.rcode, dnspython_rcode.NXDOMAIN)
        return ttl



    def __str__(self):
        """

        Put answer and ID text in string representation.

        """
        answer = self.answer

        if answer:
            answer = join(answer.to_text().splitlines(), sep=', ')

        string = join([answer, self.message.flags], sep=', ')
        string = f'{self.__class__.__name__}({string})'
        return string



@dataclass
class Request(BaseDNSData):
    """

    DNS request object.

    """
    wire: bytes

    @cached_property
    def question(self) -> RRset:
        return self.message.question[0]

    @cached_property
    def is_valid(self):
        return len(self.message.question) != 0

    @cached_property
    def type(self):
        return self.question.rdtype

    @cached_property
    def type_text(self):
        return dns.rdatatype.to_text(self.type)

    @cached_property
    def name(self):
        return self.question.name

    @cached_property
    def name_text(self):
        return self.name.to_text()

    def get_response_template(self):
        message = dns.message.make_response(self.message)
        message.flags |= dns.flags.RA
        return message

    @cached_property
    def blackhole(self) -> Response:
        blackhole = self.get_response_template()
        blackhole.set_rcode(dns.rcode.NXDOMAIN)
        response = Response.from_message(blackhole)
        return response


@dataclass
class Exchange:
    """

    Entire DNS exchange for a DNS Proxy: request -> upstream response -> response

    """
    ip: str
    port: int

    request: Request
    response: Optional[Response] = None
    answers_pre: List[RRset] = field(default_factory=list)
    is_internal: bool = False
    client_name: Optional[str] = None
    is_complete: bool = False

    @property
    def addr(self):
        return self.ip, self.port

    @classmethod
    def from_wire(cls, wire: bytes, **kwargs) -> Self:
        request = Request(wire)
        response = Response.from_message(request.get_response_template())
        return cls(request=request, response=response, **kwargs)

    @cached_property
    def client(self):
        return f'{self.ip}:{self.port}'

    @property
    def question_last(self) -> RRset:
        """

        Create an RRset surrogate representing the latest/current question.
        This can be the original question - or a hybrid one if we've injected our own answers into the Exchange.
        If there's a response, use its answers, else fall back to answers_pre, else to the original question.

        """
        answers = self.answers_pre
        if self.response:
            answers = self.response.message.answer or answers

        if answers:
            rrset = answers[-1]
            rdtype = self.request.type
            ttl = self.request.question.ttl
            rdclass = self.request.question.rdclass
            name = next(iter(rrset.items.keys())).to_text()
            rrset_surrogate = dns.rrset.from_text(
                name=name,
                ttl=ttl,
                rdtype=rdtype,
                rdclass=rdclass,
            )

            return rrset_surrogate
        else:
            return self.request.question

    @property
    def query_last(self) -> QueryMessage:
        """

        Create a query (e.g. for use by upstream) based on the last question.

        """

        question_last = self.question_last
        query = dns.message.make_query(qname=question_last.name, rdclass=question_last.rdclass, rdtype=question_last.rdtype, id=self.request.message.id)
        return query

    @property
    def key(self):
        """

        Hashable key for caching

        """
        data = tuple(self.request.question.to_text().split())
        return data

    @cached_property
    def reverse(self) -> Self:
        """

        Create an Exchange for a reverse lookup of this Exchange's client IP.

        """
        name = dnspython_reversename.from_address(self.ip)
        query = dns.message.make_query(name, dns.rdatatype.PTR)
        exchange = self.__class__.from_wire(query.to_wire(), ip=self.ip, port=self.port, is_internal=True)
        return exchange
