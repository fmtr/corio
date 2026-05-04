# Core IO (`corio`)

A collection of high-level tools that simplify everyday development work, with a focus on practical Python and AI/ML workflows.

`corio` is designed as a single utility package with opt-in extras, so projects can install only what they use.

## Install

```bash
pip install corio
```

## Quick Example

```python
import corio
from corio import Path

value = corio.env.get_int("MY_VALUE", default=None)
Path("data.json").write_json({"value": value})
```

## Documentation

- Published docs: https://fmtr.github.io/corio
- Local docs source: [docs](docs)

## License

This project is licensed under Apache 2.0. See [LICENSE](LICENSE).
