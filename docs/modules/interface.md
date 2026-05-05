# interface
`from corio import interface`

`interface` is a thin base for Flet UI apps with lifecycle hooks and typed context wiring.

Main pieces:

- `Context`: typed runtime container around `flet.Page`
- `Base`: `ft.Column` subclass with async constructor (`new`), routing hooks, and launch helper
- decorators `update` and `progress` for post-action page refresh/progress display

Install:

```bash
pip install "corio[interface]" --upgrade
```

## Typical Base Pattern

```python
import flet as ft
from corio import interface


class App(interface.Base[interface.Context]):
    TITLE = "Example Interface"

    def __init__(self):
        super().__init__(controls=[ft.Text(self.TITLE)])
```

```python
App.launch()
```

## Advanced Pattern (seen in sibling repos)

- Override `async def new(cls, page)` for async setup (database/session/bootstrap).
- Configure `PATH_ASSETS` and `PATH_UPLOADS` for static/upload handling.
- Use tabs/views and route hooks (`route`, `pop`) for multi-view apps.
- `Base` auto-manages `FLET_SECRET_KEY` when missing.

```python
@classmethod
async def new(cls, page):
    # async startup work here
    self = await super().new(page)
    return self
```

`update` and `progress` decorators are useful for callback methods that need guaranteed page refresh and spinner visibility.
