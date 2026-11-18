"""

Command and subcommand expression nodes.

"""

from __future__ import annotations

import os
import shlex
import subprocess
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable, ClassVar, NoReturn

from corio import function, logger
from corio.shell.dsl.helpers import _flatten_parts, _normalize

if TYPE_CHECKING:
    from corio.shell.dsl.args import Argument, Value
    from corio.shell.dsl.helpers import Stringable
    from corio.shell.dsl.ops import And, Or, Pipe


class ExpressionBase:
    """

    Provide shared behavior for commands and shell operations.

    """

    __isabstractmethod__: ClassVar[bool] = False

    def __and__(self, other: ExpressionBase) -> And:
        from corio.shell.dsl.ops import And

        return And(children=[self, other])

    def __or__(self, other: ExpressionBase) -> Pipe:
        from corio.shell.dsl.ops import Pipe

        return Pipe(children=[self, other])

    def __xor__(self, other: ExpressionBase) -> Or:
        from corio.shell.dsl.ops import Or

        return Or(children=[self, other])

    def argument_tokens(self) -> list[str]:
        return [str(self)]

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}('{self}')"


def _to_subcommand_part(item: Stringable | ExpressionBase) -> Argument | ExpressionBase:
    from corio.shell.dsl.args import Argument, Value

    if isinstance(item, Argument):
        return item
    if isinstance(item, Value):
        return Argument(name=item.name)
    if isinstance(item, ExpressionBase):
        return item
    return Argument(name=str(item))


def _to_expression_part(item: Stringable | ExpressionBase) -> Subcommand | Argument | ExpressionBase:
    from corio.shell.dsl.args import Argument, Value

    if isinstance(item, Subcommand):
        return item
    if isinstance(item, Argument):
        return item
    if isinstance(item, Value):
        return Argument(name=item.name)
    if isinstance(item, ExpressionBase):
        return item
    return Argument(name=str(item))


@dataclass
class Subcommand:
    """

    Represent a nested command part.

    """

    name: str
    children: list[Subcommand | Argument | ExpressionBase] = field(default_factory=list)
    active: Subcommand = field(init=False)

    def __post_init__(self) -> None:
        self.active = self

    def add_subcommand(self, name: str) -> Subcommand:
        child = Subcommand(name=name)
        self.active.children.append(child)
        self.active = child
        return child

    def __call__(self, *parts: Stringable | ExpressionBase | None) -> Subcommand:
        self.active.children.extend(_to_subcommand_part(part) for part in parts if part is not None)
        return self

    def tokens(self) -> list[str]:
        return [self.name, *_flatten_parts(self.children)]

    def argument_tokens(self) -> list[str]:
        return self.tokens()

    def __str__(self) -> str:
        return shlex.join(self.tokens())

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}('{self}')"


@dataclass(repr=False)
class Expression(ExpressionBase):
    """

    Represent a command that can be rendered or run locally.

    """

    __isabstractmethod__: ClassVar[bool] = False

    @function.ccp
    def build(cls) -> Stub:
        """

        Provide the cached command builder.

        """
        return Stub()

    name: str
    children: list[Subcommand | Argument | ExpressionBase] = field(default_factory=list)
    active: Expression | Subcommand = field(init=False)

    def __post_init__(self) -> None:
        self.active = self

    def __getattr__(self, name: str) -> Expression:
        command = _normalize(name)
        if self.active is self:
            child = Subcommand(name=command)
            self.children.append(child)
            self.active = child
            return self
        self.active = self.active.add_subcommand(command)
        return self

    def __call__(self, *parts: Stringable | ExpressionBase) -> Expression:
        if self.active is self:
            self.children.extend(_to_expression_part(part) for part in parts)
            return self
        self.active(*parts)
        return self

    def tokens(self, args_only: bool = False) -> list[str]:
        tokens = _flatten_parts(self.children)
        if args_only:
            return tokens

        tokens.insert(0, self.name)
        return tokens

    def run(
            self,
            *args: object,
            check: bool = True,
            shell: bool = False,
            **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        logger.info(str(self))
        command = str(self) if shell else self.tokens()
        result = subprocess.run(command, *args, check=check, shell=shell, **kwargs)  # type: ignore[arg-type]
        return result

    def exec(
            self,
            method: Callable[[str, list[str]], NoReturn] = os.execvp,
    ) -> NoReturn:
        logger.info(str(self))
        return method(self.name, self.tokens())

    def __iter__(self):
        logger.info(str(self))
        process = subprocess.Popen(
            self.tokens(),
            stdout=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        if process.stdout is not None:
            for line in process.stdout:
                yield line.rstrip("\n")
        process.wait()

    def __pos__(self):
        return self.run()

    def __str__(self) -> str:
        return shlex.join(self.tokens())


class Stub:
    """

    Build bare command expressions from dynamic names.

    """

    __isabstractmethod__: ClassVar[bool] = False

    def __getattr__(self, name: str) -> Expression:
        return self(_normalize(name))

    def __call__(self, name: str) -> Expression:
        return Expression(name=name)
