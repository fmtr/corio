# api
`from corio import api`

`api` provides a lightweight FastAPI base where endpoints are defined as dataclass configuration.

Main pieces:

- `Endpoint`: endpoint metadata + target method
- `Base`: app bootstrap, endpoint registration, child API mounting, and uvicorn launch helpers

Install:

```bash
pip install "corio[api]" --upgrade
```

## Typical Endpoint Pattern

```python
from corio import api


class HealthApi(api.Base):
    TITLE = "Health API"

    def get_endpoints(self):
        return [
            api.Endpoint(method_http=self.app.get, path="/health", method=self.health, tags="status"),
        ]

    async def health(self):
        """Service health."""
        return {"ok": True}
```

Run with:

```python
HealthApi.launch()
```

## Real-World Usage Pattern (generalized)

Sibling repos commonly:

- subclass `api.Base`
- keep endpoint list in `get_endpoints()`
- attach tags per feature area (`cache`, `blocking`, `documents`, etc.)
- mount child APIs using `children` when composing a larger API surface

## Notes

- `Base` instruments FastAPI via `corio.logging_tools`.
- In dev mode, exception handling is configured to re-raise for easier debugging.
- Default endpoint method is POST unless `method_http` is set.
