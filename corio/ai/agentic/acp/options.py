from typing import Any, ClassVar

from acp.schema import SessionConfigOptionSelect, SessionConfigSelectOption



DISABLED = "disabled"
APPROVAL = "approval"
FULL = "full"


class Select(SessionConfigOptionSelect):
    """

    ACP session option with a string value selected from named choices.

    """

    @property
    def value(self) -> str:
        """

        Return the currently selected option value.

        """
        return self.current_value

    @property
    def enabled(self) -> bool:
        """

        Return whether the option enables its associated behavior.

        """
        return self.value != DISABLED

    @property
    def approval(self) -> bool:
        """

        Return whether this option requires tool approval.

        """
        return self.current_value != FULL

    @classmethod
    def get_name(cls, name: str | None = None) -> str:
        """Return the select name, optionally scoped by a parent name."""
        if name is None:
            return cls.__name__
        return f"{name}/{cls.__name__}"

    @classmethod
    def from_values(
        cls,
        name: str | None = None,
        *,
        values: list[str],
        value: str,
        description: str | None,
        category: str,
        **fields: Any,
    ):
        """

        Build an ACP select option from its available values.

        """
        name = cls.get_name(name)
        return cls(
            id=name,
            name=name,
            description=description,
            category=category,
            type="select",
            currentValue=value,
            options=[
                SessionConfigSelectOption(value=item, name=item)
                for item in values
            ],
            **fields,
        )


class Policy(Select):
    """

    ACP tool access option supporting disabled, approval, and full access.

    """

    VALUES: ClassVar[list[str]] = [DISABLED, APPROVAL, FULL]

    @classmethod
    def from_value(
        cls,
        name: str,
        value: str = APPROVAL,
        description: str | None = "Tool access policy.",
    ):
        """

        Build the standard tool access policy option.

        """
        return cls.from_values(
            name=name,
            values=cls.VALUES,
            value=value,
            description=description,
            category="tools",
        )
