from enum import StrEnum

from corio.function import ccp


class MapEnum(StrEnum):
    """A string enum whose members also carry descriptions."""

    @staticmethod
    def _generate_next_value_(name, start, count, last_values):
        return name

    def __new__(cls, value: str, description: str):
        member = str.__new__(cls, value)
        member._value_ = value
        member.description = description
        return member

    @ccp
    def descriptions(cls) -> str:
        """Return the enum IDs and descriptions as a formatted list."""
        return "\n".join(
            f"{member.name}: {member.description}"
            for member in cls
        )
