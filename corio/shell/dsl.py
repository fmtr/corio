from __future__ import annotations

import os
import shlex
import subprocess
from dataclasses import dataclass, field
from typing import Callable, ClassVar, NoReturn

from corio import function, logger


def _normalize(name: str) -> str:
    underscore = "\0"
    return name.replace("__", underscore).strip("_").replace("_", "-").replace(underscore, "_")


def _to_value(item: object) -> Value | ExpressionBase:
    if isinstance(item, Value):
        return item
    if isinstance(item, Argument):
        return Value(name=item.name)
    if isinstance(item, ExpressionBase):
        return item
    return Value(name=str(item))


def _to_subcommand_part(item: object) -> Argument | ExpressionBase:
    if isinstance(item, Argument):
        return item
    if isinstance(item, Value):
        return Argument(name=item.name)
    if isinstance(item, ExpressionBase):
        return item
    return Argument(name=str(item))


def _to_expression_part(item: object) -> Subcommand | Argument | ExpressionBase:
    if isinstance(item, Subcommand):
        return item
    if isinstance(item, Argument):
        return item
    if isinstance(item, Value):
        return Argument(name=item.name)
    if isinstance(item, ExpressionBase):
        return item
    return Argument(name=str(item))


def _to_argument_child(item: object) -> Argument | Value | ExpressionBase:
    if isinstance(item, Argument):
        return item
    if isinstance(item, Value | ExpressionBase):
        return item
    return Argument(name=str(item))


def _tokens_for_part(part: Argument | Value | Subcommand | ExpressionBase) -> list[str]:
    if isinstance(part, ExpressionBase):
        return part.argument_tokens()
    return part.tokens()


def _flatten_parts(parts: list[Argument | Value | Subcommand | ExpressionBase]) -> list[str]:
    return [token for part in parts for token in _tokens_for_part(part)]


@dataclass
class Value:
    __isabstractmethod__: ClassVar[bool] = False

    name: str = ""
    children: list[object] = field(default_factory=list)

    def __getattr__(self, name: str) -> Value:
        return Value(name=_normalize(name))

    def tokens(self) -> list[str]:
        return [self.name]

    def __str__(self) -> str:
        return shlex.join(self.tokens())

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}('{self}')"


@dataclass
class Argument:
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

    def __add__(self, other: object) -> Argument:
        child = _to_value(other)
        return Argument(
            name=self.name,
            prefixes=self.prefixes,
            children=[*self.children, child],
            sep=self.sep,
        )

    def __call__(self, *parts: object) -> Argument:
        return Argument(
            name=self.name,
            prefixes=self.prefixes,
            children=[*self.children, *[_to_argument_child(part) for part in parts]],
            sep=self.sep,
        )

    def __eq__(self, other: object) -> Argument:  # type: ignore[override]
        return Argument(
            name=self.name,
            prefixes=self.prefixes,
            children=[_to_value(other)],
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
            first_token = _tokens_for_part(first)[0]
            return [f"{self.token}{self.sep}{first_token}", *_flatten_parts(rest)]
        return [self.token, *_flatten_parts(self.children)]

    def __str__(self) -> str:
        return shlex.join(self.tokens())

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}('{self}')"


@dataclass
class Subcommand:
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

    def __call__(self, *parts: object) -> Subcommand:
        self.active.children.extend(_to_subcommand_part(part) for part in parts if part is not None)
        return self

    def tokens(self) -> list[str]:
        return [self.name, *_flatten_parts(self.children)]

    def __str__(self) -> str:
        return shlex.join(self.tokens())

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}('{self}')"


class ExpressionBase:
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
    op: ClassVar[str] = "&&"
    precedence: ClassVar[int] = 1


class Or(Expressions):
    op: ClassVar[str] = "||"
    precedence: ClassVar[int] = 1


class Pipe(Expressions):
    op: ClassVar[str] = "|"
    precedence: ClassVar[int] = 2


@dataclass(repr=False)
class Expression(ExpressionBase):
    __isabstractmethod__: ClassVar[bool] = False

    @function.ccp
    def build(cls) -> Stub:
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

    def __call__(self, *parts: object) -> Expression:
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
    __isabstractmethod__: ClassVar[bool] = False

    def __getattr__(self, name: str) -> Expression:
        return self(_normalize(name))

    def __call__(self, name: str) -> Expression:
        return Expression(name=name)


arg = Argument()
val = Value()
ex = Expression.build
shell = ex
