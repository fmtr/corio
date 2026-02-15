from dataclasses import fields as get_fields_tuple

from fmtr.tools.tools import EMPTY


def get_fields(cls, **filters) -> dict:
    """

    Get a dictionary of fields from a dataclass.

    """
    fields = {}
    for field in get_fields_tuple(cls):
        if all([getattr(field, key) is value for key, value in filters.items()]):
            fields[field.name] = field

    return fields


def get_metadata(cls, **filters) -> dict:
    """

    Get a dictionary of fields metadata from a dataclass.

    """
    fields = get_fields(cls, **filters)
    metadata = {name: field.metadata for name, field in fields.items()}
    return metadata


def get_enabled_fields(cls, name, enabled=True, default=EMPTY, **filters):
    """

    Get a dictionary of fields metadata from a dataclass filtered by enabled fields.

    """
    metadata = get_metadata(cls, **filters)

    names = []

    if isinstance(name, dict):
        name = next(iter(name.keys()))

    for key, field_meta in metadata.items():

        if default is EMPTY:
            value = field_meta[name]
        else:
            value = field_meta.get(name, default)
        if value is enabled:
            names.append(key)

    return names
