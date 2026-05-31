# api
`from corio import api`

`api` provides a lightweight FastAPI base where endpoints are defined as classes.

Main pieces:

- `endpoint.Base`: base endpoint contract (`run`)
- `endpoint.API`: class-based HTTP endpoint with registration helpers
- `endpoint.MCP`: class-based MCP endpoint with tool registration helpers
- `endpoint.Tool`: MCP tool endpoint
- `endpoint.Prompt`: MCP prompt endpoint
- `endpoint.Resource`: MCP resource endpoint
- `Base`: app bootstrap, endpoint registration, child API mounting, and uvicorn launch helpers

Install:

```bash
pip install "corio[api]" --upgrade
```

## Typical Endpoint Pattern

```python
from __future__ import annotations

from corio import api
from corio.inherit import Inherit


class HealthApi(api.Base):
    TITLE = "Health API"
    
    @property
    def ENDPOINTS(self):
        return [Health]

    @property
    def TRANSFORMS(self):
        return []


class Health(Inherit[HealthApi], api.endpoint.API):
    """Service health."""

    PATH = "/health"
    TAGS = "status"

    async def run(self):
        return {"ok": True}
```

Run with:

```python
HealthApi.launch()
```

## Real-World Usage Pattern (generalized)

Sibling repos commonly:

- subclass `api.Base`
- keep endpoint class list in `ENDPOINTS` (can include `api.endpoint.API` and `api.endpoint.MCP`)
- keep MCP transform class list in `TRANSFORMS` (each class is initialized with `self.mcp`)
- attach tags per feature area (`cache`, `blocking`, `documents`, etc.)
- mount child APIs using `children` when composing a larger API surface

## Notes

- `Base` instruments FastAPI via `corio.logs`.
- In dev mode, exception handling is configured to re-raise for easier debugging.
- Endpoints register as GET routes.
- MCP endpoint classes register tools via `self.mcp.tool(...)`.
- Default endpoint path is `/{endpoint_class_name_lower}` unless `PATH` is overridden.
