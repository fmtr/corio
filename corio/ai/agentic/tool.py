from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, ClassVar, Generic, TypeVar

from corio.strings import camel_to_snake, get_docstring

if TYPE_CHECKING:
    from pydantic_ai import RunContext

    from corio.ai.agentic.toolset import Base as ToolsetBase


AgentDepsT = TypeVar("AgentDepsT", contravariant=True)


class Base(ABC, Generic[AgentDepsT]):
    """

    Base class for class-based ACP tools.

    """

    NAME: str | None = None
    DESCRIPTION: str | None = None
    TAKES_CTX: bool = True
    approve: ClassVar[bool] = False

    def __init__(self, toolset: ToolsetBase[AgentDepsT]):
        self.toolset = toolset

    @property
    def name(self) -> str:
        """

        Public tool name, defaulting to the class name in snake case.

        """
        return self.NAME or camel_to_snake(self.__class__.__name__)

    @property
    def description(self) -> str | None:
        """

        Tool description from an override or the class docstring.

        """
        if self.DESCRIPTION is not None:
            return self.DESCRIPTION
        return get_docstring(self.__class__)

    @property
    def takes_ctx(self) -> bool:
        """

        Whether this tool expects a RunContext-style first argument.

        """
        return self.TAKES_CTX

    @abstractmethod
    def run(self, *args, **kwargs):
        """

        Execute the tool.

        """
        raise NotImplementedError

    @abstractmethod
    def register(self):
        """

        Register this tool with its backing toolset.

        """
        raise NotImplementedError


class Tool(Base[AgentDepsT]):
    """

    Context-aware ACP tool.

    """

    TAKES_CTX = True

    @abstractmethod
    def run(self, ctx: RunContext[AgentDepsT], *args, **kwargs):
        """

        Execute the tool with typed run dependencies.

        """
        raise NotImplementedError

    def register(self):
        """

        Register this tool with its backing toolset.

        """
        return self.toolset.tool(
            name=self.name,
            description=self.description,
        )(self.run)


class ToolPlain(Base[AgentDepsT]):
    """

    Plain ACP tool without a RunContext-style first argument.

    """

    TAKES_CTX = False

    def register(self):
        """

        Register this tool with its backing toolset.

        """
        return self.toolset.tool_plain(
            name=self.name,
            description=self.description,
        )(self.run)
