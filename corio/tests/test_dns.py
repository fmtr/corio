import asyncio
import inspect

import dns
import pytest
from dns import rcode as dnspython_rcode

from corio.dns import client as dns_client
from corio.dns import dm as dns_dm
from corio.dns import server as dns_server


def _make_exchange(name: str = "example.com.", rdtype=dns.rdatatype.A) -> dns_dm.Exchange:
    query = dns.message.make_query(name, rdtype)
    return dns_dm.Exchange.from_wire(query.to_wire(), ip="127.0.0.1", port=5353)


def test_plain_client_resolve_is_async():
    assert inspect.iscoroutinefunction(dns_client.Plain.resolve)
    assert inspect.iscoroutinefunction(dns_client.HTTP.resolve)


def test_response_ttl_from_answers_authority_and_rcode_defaults():
    exchange = _make_exchange()
    message = exchange.request.get_response_template()
    message.answer.append(dns.rrset.from_text("example.com.", 300, "IN", "A", "1.1.1.1"))
    message.answer.append(dns.rrset.from_text("example.com.", 120, "IN", "A", "1.1.1.2"))
    response = dns_dm.Response.from_message(message)
    assert response.ttl == 120

    message = exchange.request.get_response_template()
    message.authority.append(dns.rrset.from_text("example.com.", 42, "IN", "NS", "ns1.example.com."))
    response = dns_dm.Response.from_message(message)
    assert response.ttl == 42

    message = exchange.request.get_response_template()
    message.set_rcode(dnspython_rcode.SERVFAIL)
    response = dns_dm.Response.from_message(message)
    assert response.ttl == 10

    response = dns_dm.Response.from_message(message, ttl_defaults={"SERVFAIL": 77})
    assert response.ttl == 77


def test_exchange_question_last_and_query_last_use_latest_answer_name():
    exchange = _make_exchange(name="example.com.")
    message = exchange.request.get_response_template()
    message.answer.append(dns.rrset.from_text("edge.example.com.", 60, "IN", "A", "9.9.9.9"))
    exchange.response = dns_dm.Response.from_message(message)

    question_last = exchange.question_last
    assert question_last.name.to_text() == "9.9.9.9"
    assert question_last.rdtype == exchange.request.type

    query_last = exchange.query_last
    assert query_last.question[0].name.to_text() == "9.9.9.9"
    assert query_last.id == exchange.request.message.id


def test_exchange_reverse_builds_internal_ptr_query():
    exchange = _make_exchange()
    reverse = exchange.reverse

    assert reverse.is_internal is True
    assert reverse.ip == exchange.ip
    assert reverse.port == exchange.port
    assert reverse.request.type_text == "PTR"
    assert reverse.request.name_text.endswith(".in-addr.arpa.")


@pytest.mark.asyncio
async def test_plain_client_resolve_applies_ttl_min_and_timeout(monkeypatch):
    exchange = _make_exchange()
    upstream = exchange.request.get_response_template()
    upstream.answer.append(dns.rrset.from_text("example.com.", 3, "IN", "A", "1.1.1.1"))

    async def resolve_udp(q, where, port, timeout):
        assert timeout == 1.5
        return upstream

    monkeypatch.setattr(dns_client.dnspython_asyncquery, "udp", resolve_udp)

    client_plain = dns_client.Plain(host="8.8.8.8", timeout=1.5, ttl_min=30)
    await client_plain.resolve(exchange)

    assert exchange.response.answer is not None
    assert exchange.response.answer.ttl == 30


@pytest.mark.asyncio
async def test_http_client_resolve_sets_servfail_on_exception(monkeypatch):
    exchange = _make_exchange()
    client_http = dns_client.HTTP(host="dns.google", url="https://{host}/dns-query")
    client_http._ip = "1.1.1.1"

    async def _raise(*_args, **_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(dns_client, "logger", type("L", (), {"exception": staticmethod(lambda *_args, **_kwargs: None)})())
    monkeypatch.setattr(client_http.CLIENT, "post", _raise)

    await client_http.resolve(exchange)

    assert exchange.response.rcode == dnspython_rcode.SERVFAIL
    assert exchange.is_complete is True


@pytest.mark.asyncio
async def test_http_client_resolve_has_total_timeout(monkeypatch):
    exchange = _make_exchange()
    client_http = dns_client.HTTP(
        host="dns.google",
        url="https://{host}/dns-query",
        timeout=0.01,
    )
    client_http._ip = "1.1.1.1"

    async def never_returns(*_args, **_kwargs):
        await asyncio.Event().wait()

    monkeypatch.setattr(dns_client, "logger",
                        type("L", (), {"exception": staticmethod(lambda *_args, **_kwargs: None)})())
    monkeypatch.setattr(client_http.CLIENT, "post", never_returns)

    await asyncio.wait_for(client_http.resolve(exchange), timeout=0.1)

    assert exchange.response.rcode == dnspython_rcode.SERVFAIL
    assert exchange.is_complete


@pytest.mark.asyncio
async def test_http_client_bootstrap_resolution_is_async_and_cached(monkeypatch):
    client_http = dns_client.HTTP(host="dns.google", url="https://{host}/dns-query")
    calls = 0

    async def resolve_bootstrap(exchange):
        nonlocal calls
        calls += 1
        message = exchange.request.get_response_template()
        message.answer.append(dns.rrset.from_text("dns.google.", 60, "IN", "A", "8.8.8.8"))
        exchange.response = dns_dm.Response.from_message(message)

    monkeypatch.setattr(client_http.BOOTSTRAP, "resolve", resolve_bootstrap)

    assert await client_http.get_ip() == "8.8.8.8"
    assert await client_http.get_ip() == "8.8.8.8"
    assert calls == 1


@pytest.mark.asyncio
async def test_server_sends_response_before_reverse_lookup_finishes():
    reverse_can_finish = asyncio.Event()
    response_sent = asyncio.Event()
    reverse_calls = 0

    class Transport:
        def sendto(self, data, addr):
            response_sent.set()

    class Server(dns_server.Plain):
        async def resolve(self, exchange):
            nonlocal reverse_calls
            response = exchange.request.get_response_template()
            if exchange.request.type == dns.rdatatype.PTR:
                reverse_calls += 1
                await reverse_can_finish.wait()
                response.answer.append(
                    dns.rrset.from_text(
                        exchange.request.name,
                        60,
                        "IN",
                        "PTR",
                        "client.lan.",
                    )
                )
            else:
                response.answer.append(
                    dns.rrset.from_text("example.com.", 60, "IN", "A", "1.2.3.4")
                )
            exchange.response = dns_dm.Response.from_message(response)
            exchange.is_complete = True
            return exchange

    server = Server(host="127.0.0.1", port=5353)
    server.transport = Transport()
    exchange = _make_exchange()

    await asyncio.wait_for(server.handle(exchange), timeout=0.1)
    assert response_sent.is_set()
    assert exchange.ip not in server.client_names

    reverse_can_finish.set()
    await server.wait_for_background_tasks()
    assert server.client_names[exchange.ip] == "client.lan."

    second_exchange = _make_exchange()
    await server.handle(second_exchange)
    assert second_exchange.client_name == "client.lan."
    assert reverse_calls == 1


@pytest.mark.asyncio
async def test_server_returns_servfail_when_upstream_raises():
    sent = []

    class Transport:
        def sendto(self, data, addr):
            sent.append((data, addr))

    class Server(dns_server.Plain):
        async def resolve(self, exchange):
            raise TimeoutError("upstream timed out")

    server = Server(host="127.0.0.1", port=5353)
    server.transport = Transport()
    exchange = _make_exchange()
    server.client_names[exchange.ip] = None

    await server.handle(exchange)

    assert len(sent) == 1
    response = dns.message.from_wire(sent[0][0])
    assert response.rcode() == dnspython_rcode.SERVFAIL
    assert not response.answer
    assert exchange.is_complete


@pytest.mark.asyncio
async def test_server_close_releases_transport_tasks_and_client():
    class Transport:
        closed = False

        def close(self):
            self.closed = True

    class Client:
        closed = False

        async def aclose(self):
            self.closed = True

    server = dns_server.Plain(host="127.0.0.1", port=5353)
    server.transport = Transport()
    server.client = Client()
    task = server.create_background_task(asyncio.Event().wait())
    await asyncio.sleep(0)

    await server.close()

    assert server.transport is None
    assert task.cancelled()
    assert not server.background_tasks
    assert server.client.closed
