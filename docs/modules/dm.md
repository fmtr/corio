# dm
`from corio import dm`

`dm` provides the data modelling layer built on Pydantic, with utilities aimed at robust parsing and schema ergonomics.

Highlights:

- `Field`: reusable field definitions with optional auto-defaulting and title/description templating
- `Base`: model base that can aggregate `FIELDS` declarations across inheritance
- `to_df`: quick conversion to tabular representation (`tabular` extra needed there)

Install:

```bash
pip install "corio[dm]" --upgrade
```

## Typical Model Pattern

```python
from corio import dm


class User(dm.Base):
    id: int
    name: str


user = User.model_validate_json('{"id": 1, "name": "Ada"}')
```

## Field Class Pattern

`dm.Field` is useful when you want reusable field components across multiple models:

```python
from corio import dm


class FieldName(dm.Field):
    ANNOTATION = str
    DESCRIPTION = "Human-readable user name."


class User(dm.Base):
    FIELDS = [FieldName]
    id: int
```

## CLI Integration

`Base.run()` enables subcommand-style `run()` flow for settings/models that integrate with `pydantic-settings`
subcommands.
