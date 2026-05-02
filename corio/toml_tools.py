import tomllib
from typing import Any


def from_toml(toml_str: str) -> Any:
    """

    Deserialize from TOML.

    """
    return tomllib.loads(toml_str)


def to_toml(obj: Any) -> str:
    """

    Serialize to TOML.

    """
    import tomlkit

    return tomlkit.dumps(obj)


def get_table(data: dict, path: tuple[str, ...]) -> dict | None:
    """

    Get nested table by path.

    """
    table = data
    for key in path:
        if not isinstance(table, dict) or key not in table:
            return None
        table = table[key]

    if not isinstance(table, dict):
        return None
    return table


def ensure_table(data: dict, path: tuple[str, ...]) -> dict:
    """

    Ensure nested table exists and return it.

    """
    table = data
    for key in path:
        value = table.get(key)
        if not isinstance(value, dict):
            value = {}
            table[key] = value
        table = value
    return table
