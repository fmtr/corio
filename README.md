# Corio

Corio is a practical Python toolkit for building small services, automation, data pipelines, and AI/ML support code without re-solving the same project plumbing every time.

It bundles the pieces that tend to sit between "standard library" and "application code": typed paths with serialization helpers, pydantic-friendly data models, CLI settings, structured logging spans, iterator progress, FastAPI/MCP endpoint scaffolding, release metadata generation, test environment generation, and opt-in integrations for docs, Docker, search, tabular data, PDFs, OpenAI, Home Assistant, DNS, caching, encryption, and more.

Corio is organized as one package with optional extras. Install the small core by default, then opt into the heavier tools a project actually needs.

## Install

```bash
pip install corio
```

Examples:

```bash
pip install "corio[api]"
pip install "corio[tabular]"
pip install "corio[db.search]"
pip install "corio[infra]"
```

## Why Use It

- **Use paths as real application objects.** Read and write JSON, YAML, TOML, text, and derived paths directly from `corio.Path`.
- **Make CLIs from typed models.** Corio builds on pydantic settings patterns so small tools can stay declarative.
- **Wrap iteration with observability.** `corio.iterator.Iterator` tracks count, percentage, elapsed time, ETA, completion, and cleanup.
- **Expose tools as HTTP and MCP endpoints.** Define endpoint classes once and mount them into FastAPI and MCP surfaces.
- **Keep release metadata generated.** `corio pyproject` turns Corio dependency groups and project metadata into the generated `pyproject.toml` sections.
- **Install integrations only when needed.** Extras keep heavy dependencies like API servers, vector search, ML, PDFs, and tabular tooling out of the base install.

## Examples

### Typed Paths And Data Files

```python
from corio import Path

path = Path("runs/latest/config.yaml")
path.parent.mkdirf()
path.write_data({
    "model": "embedder-v2",
    "batch_size": 64,
})

config = path.read_data()
json_path = path.get_conversion_path("json")
json_path.parent.mkdirf()
json_path.write_data(config)
```

### Observable Iteration

```python
from corio.iterator import Iterator

documents = [{"id": "a"}, {"id": "b"}, {"id": "c"}]

for document in Iterator(documents):
    # Work happens inside per-item logging spans with progress stats.
    process(document)
```

The iterator tracks `count`, `total`, `percentage`, elapsed time, rate, ETA, completion logs, and closes the wrapped iterator when possible.

### FastAPI And MCP Tools

```python
from functools import cached_property

from corio import api


class Search(api.endpoint.API):
    """Search indexed documents."""

    PATH = "/search"
    TAGS = "documents"

    async def run(self, query: str):
        return {"query": query, "results": []}


class Reindex(api.endpoint.Tool):
    """Rebuild the document index."""

    async def run(self):
        return {"status": "queued"}


class Service(api.Base):
    TITLE = "Document Service"
    PORT = 8080

    @cached_property
    def ENDPOINTS(self):
        return [Search, Reindex]


Service().launch()
```

The same endpoint model can feed HTTP routes and MCP tools, so internal automation and external APIs stay aligned.

### Project Metadata

Corio projects keep dependency intent in `[tool.corio.dependencies]`; generated package metadata lives in `[project.optional-dependencies]`.

```toml
[tool.corio.dependencies]
semantic = ["sentence_transformers", "metrics"]
metrics = ["tabular", "ranx"]
tabular = ["pandas", "tabulate", "openpyxl", "odfpy", "deepdiff"]
```

Then regenerate:

```bash
corio pyproject
```

That keeps extras flattened for packaging while preserving a maintainable source-of-truth dependency graph.

## Useful Areas

- `corio.path`: typed path helpers, app paths, file type guessing, serialization helpers.
- `corio.dm` and `corio.sets`: pydantic-oriented models and settings/CLI support.
- `corio.api`: FastAPI and MCP endpoint composition.
- `corio.iterator`: progress-aware iterable wrapper and small collection helpers.
- `corio.infra`: release, docs, tox, and pyproject generation tooling.
- `corio.db.search`: vector search helpers around qdrant and embeddings.
- `corio.tabular`, `corio.semantic`, `corio.metric`: data and retrieval metrics helpers.
- `corio.encrypt`, `corio.sec`: project secret and encryption workflows.
- `corio.ha`, `corio.dns`, `corio.mqtt`, `corio.webhook`: operations and home automation integrations.

## Documentation

- Published docs: https://fmtr.github.io/corio
- Local docs source: [docs](docs)

## License

This project is licensed under Apache 2.0. See [LICENSE](LICENSE).
