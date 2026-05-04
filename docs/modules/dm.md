# `from corio import dm`

`dm` provides the data modelling layer built on Pydantic, with utilities aimed at robust parsing and schema ergonomics.

Highlights:

- `Field`: reusable field definitions with optional auto-defaulting and title/description templating
- `Base`: model base that can aggregate `FIELDS` declarations across inheritance
- `MixinFromJson`: tolerant `from_json` flow (especially useful for LLM output cleanup)
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


user = User.from_json('{"id": 1, "name": "Ada"}')
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

## LLM/Unclean JSON Use

`MixinFromJson` routes through `json_fix` when available, so model parsing can be more tolerant than strict `model_validate_json`.

This is especially useful for:

- tool-call payload recovery
- partially malformed JSON responses
- low-friction CLI/data ingestion flows

## CLI Integration

`CliRunMixin` enables subcommand-style `run()` flow for settings/models that integrate with `pydantic-settings` subcommands.
