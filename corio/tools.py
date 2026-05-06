from typing import Any


def identity(x: Any) -> Any:
    """

    Dummy (identity) function

    """
    return x


class Special:
    """

    Classes to differentiate special arguments from primitive arguments.

    """


class Empty(Special):
    """

    Class to denote an unspecified object (e.g. argument) when `None` cannot be used.

    """


class Raise(Special):
    """

    Class to denote when a function should raise instead of e.g. returning a default.

    """


class Auto(Special):
    """

    Class to denote when an argument should be inferred.

    """


class Required(Special):
    """

    Class to denote when an argument is required.

    """



EMPTY = Empty()
