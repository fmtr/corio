from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING

from pydantic_ai.toolsets import FunctionToolset

from corio.iterator import IndexList

from corio.ai.agentic.tool import Base as ToolBase


class Base(FunctionToolset):
    """

    Class-based ACP toolset scaffold.

    """

    def __init__(self):
        super().__init__()
        for tool in self.tool_instances:
            tool.register()

    @cached_property
    def TOOLS(self) -> list[type[ToolBase]]:
        """

        Tool classes registered on this toolset.

        """
        return []

    @cached_property
    def tool_instances(self) -> IndexList[ToolBase]:
        """

        Instantiated tool objects for this toolset.

        """
        return IndexList(tool_cls(self) for tool_cls in self.TOOLS)
