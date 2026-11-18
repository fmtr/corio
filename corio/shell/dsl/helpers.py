"""

Shared naming and token helpers for the shell DSL.

"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from corio.shell.dsl.args import Argument, Value
    from corio.shell.dsl.expression import Subcommand
    from corio.shell.dsl.expression import ExpressionBase


class Stringable(Protocol):
    """

    Describe values that can be rendered as a command token.

    """

    def __str__(self) -> str: ...


def _normalize(name: str) -> str:
    """

    Convert Python-style attribute names to shell names.

    """
    underscore = "\0"
    return name.replace("__", underscore).strip("_").replace("_", "-").replace(underscore, "_")


def _tokens_for_part(part: Argument | Value | Subcommand | ExpressionBase) -> list[str]:
    """

    Render a DSL node in the single-token context of a parent command.

    """
    return part.argument_tokens()


def _flatten_parts(parts: list[Argument | Value | Subcommand | ExpressionBase]) -> list[str]:
    """

    Flatten child nodes into command tokens.

    """
    return [token for part in parts for token in _tokens_for_part(part)]
