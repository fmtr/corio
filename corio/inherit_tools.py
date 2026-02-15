from typing import TypeVar, Generic

T = TypeVar("T")


class Inherit(Generic[T]):
    """

    Runtime inheritance. Acts like a wrapper around an instantiated base class of type T, and allows overriding methods in subclasses like regular inheritance.

    """

    def __init__(self, parent: T):
        """

        Set parent

        """
        object.__setattr__(self, "_parent", parent)

    def __getattribute__(self, name):
        """

        Since regular attribute access checks own methods first, we don't need to do anything fancy to fall back to the parent when not implemented.

        """

        cls = object.__getattribute__(self, "__class__")
        attr = cls.__dict__.get(name, None)
        if attr is not None and hasattr(attr, "__get__"):
            # descriptor on self class, call normally
            return attr.__get__(self, cls)
        try:
            return object.__getattribute__(self, name)
        except AttributeError:
            parent = object.__getattribute__(self, "_parent")
            return getattr(parent, name)

    @property
    def inherit_parent(self) -> T:
        """

        Retrieves the inherit parent `_parent` attribute.

        """
        return object.__getattribute__(self, "_parent")

    @property
    def inherit_root(self):
        """

        Returns the root object in the inheritance hierarchy.

        """
        cur = object.__getattribute__(self, "_parent")
        while isinstance(cur, Inherit):
            cur = object.__getattribute__(cur, "_parent")
        return cur
