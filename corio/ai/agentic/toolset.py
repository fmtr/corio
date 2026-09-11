from __future__ import annotations

from functools import cached_property, partial
from pydantic import validate_call
from pydantic_ai import RunContext
from pydantic_ai.tools import ToolDefinition
from pydantic_ai.toolsets import FunctionToolset
from typing import TYPE_CHECKING, Any, Generic, TypeVar

from corio import strings
from corio.ai.agentic import tool
from corio.ai.agentic.approval import ApprovalMetadata, ApprovalRequiredToolsetMetadata
from corio.iterator import ilist
from corio.strings import get_docstring, join_natural


AgentDepsT = TypeVar("AgentDepsT", contravariant=True)


class Base(FunctionToolset[AgentDepsT], Generic[AgentDepsT]):
    """

    Class-based ACP toolset scaffold.

    """

    DESCRIPTION: str | None = None

    def __init__(self):
        super().__init__()
        for tool in self.tool_instances:
            tool.register()

    @property
    def id(self) -> str:
        """

        Return the toolset identifier used by pydantic-ai.

        """
        return self.name

    @property
    def name(self) -> str:
        """

        Return the concrete toolset class name.

        """
        return type(self).__name__


    @property
    def description(self) -> str | None:
        """

        Toolset description from an override or the class docstring.

        """
        if self.DESCRIPTION is not None:
            return self.DESCRIPTION
        return get_docstring(self.__class__)

    @cached_property
    def TOOLS(self) -> list[type[tool.Base[AgentDepsT]]]:
        """

        Tool classes registered on this toolset.

        """
        return []

    @cached_property
    def tool_instances(self) -> ilist[tool.Base[AgentDepsT]]:
        """

        Instantiated tool objects for this toolset.

        """
        return ilist[tool.Base[AgentDepsT]](tool_cls(self) for tool_cls in self.TOOLS)

    async def get_instructions(self, ctx: RunContext[AgentDepsT]) -> list[str]:
        """

        Tool instructions derived from the registered toolset.

        """
        names = self.tool_instances.name.keys()
        names = join_natural(names, mask='`{}`')
        return [
            strings.trim(
                f"""
                ## {self.description}

                You have access to {self.description} like {names}.
                """
            )
        ]

    # ACP-related:

    if TYPE_CHECKING:
        from corio.ai.agentic.acp import options


    def approve(
            self,
            ctx: RunContext[AgentDepsT],
            tool_def: ToolDefinition,
            tool_args: dict[str, Any],
    ) -> ApprovalMetadata | bool:
        """

        Decide whether a tool call requires user approval, and if so why.

        """

        if not self.option.approval:
            return False

        tool = self.tool_instances.name[tool_def.name]
        if isinstance(tool.approve, bool):
            return tool.approve
        tool_approve = validate_call(partial(tool.approve, ctx))
        msgs = tool_approve(**tool_args)
        return ApprovalMetadata(msgs=msgs)


    @cached_property
    def wrapper(self) -> ApprovalRequiredToolsetMetadata[AgentDepsT]:
        """

        Return the approval-enforcing view of this toolset.

        """
        return ApprovalRequiredToolsetMetadata[AgentDepsT](self, self.approve)

    @cached_property
    def option(self) -> options.Policy:
        """

        Return the default full-access policy for this toolset.

        """
        from corio.ai.agentic.acp import options
        return options.Policy.from_value(
            name=self.name,
            value=options.FULL,
            description=self.description,
        )
