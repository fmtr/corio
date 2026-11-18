"""

Shell operator expressions and their shared behavior.

"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar


class ExpressionBase:
    """

    Provide shared behavior for commands and shell operations.

    """

    __isabstractmethod__: ClassVar[bool] = False

    def __and__(self, other: ExpressionBase) -> And:
        return And(children=[self, other])

    def __or__(self, other: ExpressionBase) -> Pipe:
        return Pipe(children=[self, other])

    def __xor__(self, other: ExpressionBase) -> Or:
        return Or(children=[self, other])

    def argument_tokens(self) -> list[str]:
        return [str(self)]

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}('{self}')"


@dataclass(repr=False)
class Expressions(ExpressionBase):
    """

    Combine expression nodes using shell operator syntax.

    """

    children: list[ExpressionBase] = field(default_factory=list)

    op: ClassVar[str] = ""
    precedence: ClassVar[int] = 0

    def tokens(self) -> list[str]:
        return [str(self)]

    def _needs_parentheses(self, child: ExpressionBase, index: int) -> bool:
        if not isinstance(child, Expressions):
            return False
        if child.precedence < self.precedence:
            return True
        if child.precedence > self.precedence:
            return False
        if index == 0:
            return False
        return child.op != self.op

    def __str__(self) -> str:
        parts = []
        for index, child in enumerate(self.children):
            child_text = str(child)
            if self._needs_parentheses(child, index):
                child_text = f"({child_text})"
            parts.append(child_text)

        return f" {self.op} ".join(parts)


class And(Expressions):
    """

    Join commands with shell's success-only operator.

    """

    op: ClassVar[str] = "&&"
    precedence: ClassVar[int] = 1


class Or(Expressions):
    """

    Join commands with shell's failure-only operator.

    """

    op: ClassVar[str] = "||"
    precedence: ClassVar[int] = 1


class Pipe(Expressions):
    """

    Connect one command's output to another command's input.

    """

    op: ClassVar[str] = "|"
    precedence: ClassVar[int] = 2
