from __future__ import annotations

import os
import shlex
import subprocess
from dataclasses import dataclass, field
from typing import Callable, ClassVar, NoReturn

from corio import logger


def _normalize(name: str) -> str:
    underscore = "\0"
    return name.replace("__", underscore).strip("_").replace("_", "-").replace(underscore, "_")


def _to_value(item: object) -> Value:
    if isinstance(item, Value):
        return item
    if isinstance(item, Argument):
        return Value(name=item.name)
    return Value(name=str(item))


def _to_subcommand_part(item: object) -> Argument:
    if isinstance(item, Argument):
        return item
    if isinstance(item, Value):
        return Argument(name=item.name)
    return Argument(name=str(item))


def _to_expression_part(item: object) -> Subcommand | Argument:
    if isinstance(item, Subcommand):
        return item
    if isinstance(item, Argument):
        return item
    if isinstance(item, Value):
        return Argument(name=item.name)
    return Argument(name=str(item))


def _to_argument_child(item: object) -> Argument | Value:
    if isinstance(item, Argument):
        return item
    if isinstance(item, Value):
        return item
    return Argument(name=str(item))


def _flatten_parts(parts: list[object]) -> list[str]:
    return [token for part in parts for token in part.tokens()]


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
    children: list[Argument | Value] = field(default_factory=list)
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
            return [f"{self.token}{self.sep}{first.tokens()[0]}", *_flatten_parts(rest)]
        return [self.token, *_flatten_parts(self.children)]

    def __str__(self) -> str:
        return shlex.join(self.tokens())

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}('{self}')"


@dataclass
class Subcommand:
    name: str
    children: list[Subcommand | Argument] = field(default_factory=list)
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


@dataclass
class Expression:
    __isabstractmethod__: ClassVar[bool] = False

    name: str
    shell: Shell
    children: list[Subcommand | Argument] = field(default_factory=list)
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

    def tokens(self) -> list[str]:
        return [self.name, *_flatten_parts(self.children)]

    def run(
            self,
            *args: object,
            check: bool = True,
            shell: bool = False,
            **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        return self.shell.run(self, *args, check=check, shell=shell, **kwargs)

    def exec(
            self,
            method: Callable[[str, list[str]], NoReturn] = os.execvp,
    ) -> NoReturn:
        return self.shell.exec(self, method=method)

    def __iter__(self):
        return self.shell.__iter__(self)

    def __pos__(self):
        return self.run()

    def __str__(self) -> str:
        return shlex.join(self.tokens())

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}('{self}')"


@dataclass
class Shell:
    __isabstractmethod__: ClassVar[bool] = False

    context: str = ""

    def __getattr__(self, name: str | None) -> Expression:
        return self(_normalize(name))

    def __call__(self, name: str) -> Expression:
        return Expression(name=name, shell=self)

    def __iter__(self, expression: Expression):
        logger.info(str(expression))
        process = subprocess.Popen(
            expression.tokens(),
            stdout=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        if process.stdout is not None:
            for line in process.stdout:
                yield line.rstrip("\n")
        process.wait()

    def run(
            self,
            expression: Expression,
            *args: object,
            check: bool = True,
            shell: bool = False,
            **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        logger.info(str(expression))
        command = str(expression) if shell else expression.tokens()
        result = subprocess.run(command, *args, check=check, shell=shell, **kwargs)  # type: ignore[arg-type]
        return result

    def exec(
            self,
            expression: Expression,
            method: Callable[[str, list[str]], NoReturn] = os.execvp,
    ) -> NoReturn:
        logger.info(str(expression))
        return method(expression.name, expression.tokens())

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}('{self.context}')"


arg = Argument()
val = Value()
shell = Shell()
