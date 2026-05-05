# patterns
`from corio import patterns`

`patterns` is a regex-driven transformation utility for structured rewrite rules.

Main types:

- `Key`: serializable pattern key with named capture support
- `Item`: source/target rule pair
- `Transformer`: compiles many rules into one expression and applies one-pass or recursive rewrite

Install:

```bash
pip install "corio[patterns]" --upgrade
```

## Why Use It

Use this when dictionary-style lookups are not enough and you need:

- regex capture groups
- templated target rewrites
- recursive transforms with loop detection

## Real-world Pattern (generalized)

In DNS tooling, repos use:

- `Key` subclasses (`name`, `records`)
- `Item` rules mapping a source key to transformed key or sentinel value
- `Transformer.get(key)` to select upstream behavior or blocklist output

## Example

```python
from dataclasses import dataclass
from corio import patterns


@dataclass
class HostKey(patterns.Key):
    FILLS = {"sub": r"[a-z0-9-]+"}
    host: str


rules = [
    patterns.Item(source=HostKey(host=r"{sub}\.example\.com"), target=HostKey(host=r"edge-{sub}.example.net")),
]

tx = patterns.Transformer(items=rules, default=None)
```

If recursive mode is enabled and rules loop, `RewriteCircularLoopError` is raised.
