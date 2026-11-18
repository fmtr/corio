"""

Argument and value nodes for shell expressions.

"""

from __future__ import annotations

import shlex
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, ClassVar

from corio.shell.dsl.helpers import _flatten_parts, _normalize
from corio.shell.dsl.ops import ExpressionBase

if TYPE_CHECKING:
    from corio.shell.dsl.helpers import Stringable


def _to_value(item: Stringable | ExpressionBase) -> Value | ExpressionBase:
    if isinstance(item, Value):
        return item
    if isinstance(item, Argument):
        return Value(name=item.name)
    if isinstance(item, ExpressionBase):
        return item
    return Value(name=str(item))


def _to_argument_child(item: Stringable | ExpressionBase) -> Argument | Value | ExpressionBase:
    if isinstance(item, Argument):
        return item
    if isinstance(item, Value | ExpressionBase):
        return item
    return Argument(name=str(item))


@dataclass
class Value:
    """

    Represent a single value token.

    """

    __isabstractmethod__: ClassVar[bool] = False

    name: str = ""

    def __getattr__(self, name: str) -> Value:
        return Value(name=_normalize(name))

    def tokens(self) -> list[str]:
        return [self.name]

    def argument_tokens(self) -> list[str]:
        return self.tokens()

    def __str__(self) -> str:
        return shlex.join(self.tokens())

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}('{self}')"


@dataclass
class Argument:
    """

    Build an option token with prefixes and child values.

    """

    __isabstractmethod__: ClassVar[bool] = False

    name: str = ""
    prefixes: str = ""
    children: list[Argument | Value | ExpressionBase] = field(default_factory=list)
    sep: str = " "

    def __getattr__(self, name: str) -> Argument:
        return Argument(name=_normalize(name), prefixes=self.prefixes)

    def __neg__(self) -> Argument:
        return Argument(name=self.name, prefixes=f"-{self.prefixes}", children=list(self.children), sep=self.sep)

    def __pos__(self) -> Argument:
        return Argument(name=self.name, prefixes=f"+{self.prefixes}", children=list(self.children), sep=self.sep)

    def __add__(self, other: Stringable | ExpressionBase) -> Argument:
        child = _to_value(other)
        return Argument(
            name=self.name,
            prefixes=self.prefixes,
            children=[*self.children, child],
            sep=self.sep,
        )

    def __call__(self, *parts: Stringable | ExpressionBase) -> Argument:
        return Argument(
            name=self.name,
            prefixes=self.prefixes,
            children=[*self.children, *[_to_argument_child(part) for part in parts]],
            sep=self.sep,
        )

    def __eq__(self, other: object) -> Argument:  # type: ignore[override]
        if isinstance(other, Argument | Value | ExpressionBase):
            child = _to_value(other)
        else:
            child = Value(name=str(other))
        return Argument(
            name=self.name,
            prefixes=self.prefixes,
            children=[child],
            sep="=",
        )

    @property
    def token(self) -> str:
        return f"{self.prefixes}{self.name}"

    def tokens(self) -> list[str]:
        if not self.children:
            return [self.token]
        if self.sep != " ":
            first, rest = self.children[0], self.children[1:]
            first_token = _flatten_parts([first])[0]
            return [f"{self.token}{self.sep}{first_token}", *_flatten_parts(rest)]
        return [self.token, *_flatten_parts(self.children)]

    def argument_tokens(self) -> list[str]:
        return self.tokens()

    def __str__(self) -> str:
        return shlex.join(self.tokens())

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}('{self}')"


arg = Argument()
val = Value()
