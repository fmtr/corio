from __future__ import annotations

from functools import cached_property
from typing import Generic, Self, TypeVar
from pydantic_ai import ApprovalRequiredToolset, ApprovalRequired, WrapperToolset

from corio import dm


class ApprovalMetadata(dm.Base):
    """

    Structured approval diagnostics shared by toolsets and approval transports.

    """

    msgs: list[str] = []

    def __bool__(self) -> bool:
        """

        Treat metadata without diagnostics as no approval requirement.

        """
        return bool(self.msgs)

    @cached_property
    def text(self) -> str:
        """

        Return diagnostics flattened for display in an approval request.

        """
        return "\n".join(self.msgs)

    @classmethod
    def from_bool(cls, value: bool) -> Self:
        """

        Convert a boolean approval decision into structured metadata.

        """
        if not value:
            return cls()
        return cls(msgs=["Approval required"])


AgentDepsT = TypeVar("AgentDepsT", contravariant=True)


class ApprovalRequiredToolsetMetadata(
    ApprovalRequiredToolset[AgentDepsT],
    Generic[AgentDepsT],
):
    """

    Preserve structured approval diagnostics before serializing them for pydantic-ai.

    """

    async def call_tool(self, name, tool_args, ctx, tool):
        """

        Convert structured approval metadata to pydantic-ai's wire format.

        """
        metadata = None
        if not ctx.tool_call_approved:
            metadata = self.approval_required_func(ctx, tool.tool_def, tool_args)
            if isinstance(metadata, bool):
                metadata = ApprovalMetadata.from_bool(metadata)

        if metadata:
            raise ApprovalRequired(metadata.model_dump())

        return await WrapperToolset.call_tool(self, name, tool_args, ctx, tool)
