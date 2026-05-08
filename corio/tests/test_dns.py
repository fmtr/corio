import dns
from dns import rcode as dnspython_rcode

from corio.dns import client as dns_client
from corio.dns import dm as dns_dm


def _make_exchange(name: str = "example.com.", rdtype=dns.rdatatype.A) -> dns_dm.Exchange:
    query = dns.message.make_query(name, rdtype)
    return dns_dm.Exchange.from_wire(query.to_wire(), ip="127.0.0.1", port=5353)


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


def test_plain_client_resolve_applies_ttl_min(monkeypatch):
    exchange = _make_exchange()
    upstream = exchange.request.get_response_template()
    upstream.answer.append(dns.rrset.from_text("example.com.", 3, "IN", "A", "1.1.1.1"))

    monkeypatch.setattr(dns_client.dnspython_query, "udp", lambda q, where, port: upstream)

    client_plain = dns_client.Plain(host="8.8.8.8", ttl_min=30)
    client_plain.resolve(exchange)

    assert exchange.response.answer is not None
    assert exchange.response.answer.ttl == 30


def test_http_client_resolve_sets_servfail_on_exception(monkeypatch):
    exchange = _make_exchange()
    client_http = dns_client.HTTP(host="dns.google", url="https://{host}/dns-query")
    client_http.__dict__["ip"] = "1.1.1.1"

    def _raise(*_args, **_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(dns_client, "logger", type("L", (), {"exception": staticmethod(lambda *_args, **_kwargs: None)})())
    monkeypatch.setattr(client_http.CLIENT, "post", _raise)

    client_http.resolve(exchange)

    assert exchange.response.rcode == dnspython_rcode.SERVFAIL
    assert exchange.response.is_complete is True
