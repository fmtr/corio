from fmtr.tools.tools import MissingExtraError


class MissingExtraMockModule:
    """

    Mock module for when extras for a given module are missing. Will raise if said module is used.

    """

    def __init__(self, extra: str, exception: ImportError):
        self.extra = extra
        self.exception = exception

    def __getattr__(self, name):
        self()

    def __call__(self, *args, **kwargs):
        """

        Raise MissingExtraError if module is missing - from the original import error.

        """

        raise MissingExtraError(self.extra) from self.exception
