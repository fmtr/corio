from __future__ import annotations

from functools import cached_property
from typing import Any

from pydantic_ai import RunContext
from pydantic_ai.toolsets import FunctionToolset

from corio import strings
from corio.ai.agentic import tool
from corio.iterator import IndexList
from corio.strings import get_docstring, join_natural


class Base(FunctionToolset):
    """

    Class-based ACP toolset scaffold.

    """

    DESCRIPTION: str | None = None

    def __init__(self):
        super().__init__()
        for tool in self.tool_instances:
            tool.register()

    @property
    def description(self) -> str | None:
        """

        Toolset description from an override or the class docstring.

        """
        if self.DESCRIPTION is not None:
            return self.DESCRIPTION
        return get_docstring(self.__class__)

    @cached_property
    def TOOLS(self) -> list[type[tool.Base]]:
        """

        Tool classes registered on this toolset.

        """
        return []

    @cached_property
    def tool_instances(self) -> IndexList[tool.Base]:
        """

        Instantiated tool objects for this toolset.

        """
        return IndexList[tool.Base](tool_cls(self) for tool_cls in self.TOOLS)

    async def get_instructions(self, ctx: RunContext[Any]) -> list[str]:
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
