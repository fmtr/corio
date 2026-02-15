from fmtr.tools.constants import Constants
from typing import Any


class MissingExtraError(ImportError):
    """

    Error to raise if extras are missing.

    """

    MASK = 'The current module is missing dependencies. To install them, run: `pip install {library}[{extra}] --upgrade`'

    def __init__(self, extra):
        self.message = self.MASK.format(library=Constants.LIBRARY_NAME, extra=extra)

        super().__init__(self.message)


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
