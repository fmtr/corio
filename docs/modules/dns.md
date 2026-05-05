# dns
`from corio import dns`

`dns` contains a small DNS toolkit for building resolvers/proxies, with request/response datamodels and plain or DoH upstream clients.

Main parts:

- `dns.dm`: exchange/request/response models (`Exchange`, `Request`, `Response`)
- `dns.client`: upstream clients (`Plain`, `HTTP`)
- `dns.server`: async UDP server base with caching and structured handling
- `dns.proxy`: proxy server base that lets you hook `process_question` and `process_upstream`

Install:

```bash
pip install "corio[dns]" --upgrade
```

## Request Flow

The base `dns.proxy.Proxy` model is stage-based:

1. `process_question(exchange)` - mutate/short-circuit before upstream.
2. upstream resolve (`dns.client.Plain` or `dns.client.HTTP`).
3. `process_upstream(exchange)` - inspect/replace upstream answers.
4. `finalize(exchange)` - finalize message and completion state.

`dns.server.Plain` handles UDP datagrams, cache check/write, reverse lookup context, and response send.

```python
from corio import dns


class PolicyProxy(dns.proxy.Proxy):
    def process_question(self, exchange):
        # rewrite or block before upstream
        return

    def process_upstream(self, exchange):
        # inspect upstream answers, optionally block
        return
```

## Upstream Selection

`dns.client.HTTP` is used for DoH, and can be selected dynamically by wrapping clients in a rule-driven selector (for example via `patterns.Transformer` subclasses).

## Data Model Objects

- `dns.dm.Request`: parsed question and helper metadata.
- `dns.dm.Response`: response/message wrapper with `rcode`, `ttl`, answer access.
- `dns.dm.Exchange`: mutable exchange state from ingress to final response.

