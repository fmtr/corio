import builtins
from types import ModuleType
from typing import Any


class MissingExtraError(ImportError):
    """
    Error to raise when optional extras are missing.
    """

    MASK = 'The current module is missing dependencies. To install them, run: `pip install {library}[{extra}] --upgrade`'

    def __init__(self, extra: str):
        from corio.paths import paths
        message = self.MASK.format(library=paths.name_ns, extra=extra)
        super().__init__(message)


class MissingExtraMockModule:
    """
    Mock module used when optional dependencies are missing.
    Any attribute access or call raises `MissingExtraError` chained from the
    original import exception.
    """

    def __init__(self, extra: str, exception: ImportError):
        self.extra = extra
        self.exception = exception

    def __getattr__(self, name: str) -> Any:
        self()

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        raise MissingExtraError(self.extra) from self.exception


class ImportHook:
    """
    Import hook that translates missing optional dependencies in `corio.*`
    imports into `MissingExtraError`.
    """

    def __init__(self, auto_register: bool = True) -> None:
        self._previous_import = None
        if auto_register:
            self.register()

    @property
    def is_registered(self) -> bool:
        """
        Return whether this hook is currently installed as `builtins.__import__`.
        """
        return builtins.__import__ is self

    def __call__(
        self,
        name: str,
        globals: dict[str, Any] | None = None,
        locals: dict[str, Any] | None = None,
        fromlist: tuple[str, ...] = (),
        level: int = 0,
    ) -> ModuleType:
        """
        Delegate to the original importer and convert `ModuleNotFoundError`
        from `corio.*` callers into `MissingExtraError`.
        """
        caller_name = (globals or {}).get('__name__', '')
        if self._previous_import is None:
            raise RuntimeError('ImportHook is not registered')
        try:
            return self._previous_import(name, globals, locals, fromlist, level)
        except ModuleNotFoundError as exception:
            if not caller_name.startswith('corio'):
                raise
            if caller_name == 'corio':
                raise
            extra = caller_name[len('corio.'):]
            raise MissingExtraError(extra) from exception

    def register(self) -> None:
        """
        Install this hook into `builtins.__import__`.
        """
        if self.is_registered:
            return
        self._previous_import = builtins.__import__
        builtins.__import__ = self

    def deregister(self) -> None:
        """
        Restore the original `builtins.__import__`.
        """
        if not self.is_registered:
            return
        builtins.__import__ = self._previous_import
        self._previous_import = None
