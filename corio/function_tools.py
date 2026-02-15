import functools
import inspect
from fmtr.tools import context_tools
from typing import Tuple, Callable, Self


def combine_args_kwargs(args: dict=None, kwargs: dict=None) -> dict:
    """

    Combines arguments and keyword arguments into a single dictionary.

    """
    args = args or []
    kwargs = kwargs or {}
    args = {i: arg for i, arg in enumerate(args)}
    args.update(kwargs)
    if all(isinstance(key, int) for key in args.keys()):
        args = list(args.values())
    return args


def split_args_kwargs(args_kwargs: dict) -> Tuple[list, dict]:
    """

    Splits arguments and keyword arguments into a list and a dictionary.

    """
    if isinstance(args_kwargs, list):
        args, kwargs = args_kwargs, {}
    else:
        args = [arg for key, arg in args_kwargs.items() if isinstance(key, int)]
        kwargs = {key: arg for key, arg in args_kwargs.items() if not isinstance(key, int)}

    return args, kwargs


class MethodDecorator:
    """

    Bound method decorator with overridable start/stop and context manager

    """

    CONTEXT_KEY = 'context'

    def __init__(self):
        """

        Initialise the decorator itself with any arguments

        """
        self.func = None

    def __call__(self, func: Callable) -> Self:
        """

        Add the (unbound) method.

        """
        self.func = func
        functools.update_wrapper(self, func)
        return self

    def __get__(self, instance, owner):
        """

        Wrap bound method at runtime, call start/stop within context.

        """
        if instance is None:  # Class method called.
            return self.func

        if inspect.iscoroutinefunction(self.func):
            async def async_wrapper(*args, **kwargs):
                with self.get_context(instance):
                    self.start(instance, *args, **kwargs)
                    result = await self.func(instance, *args, **kwargs)
                    self.stop(instance, *args, **kwargs)
                    return result

            return async_wrapper

        else:
            def sync_wrapper(*args, **kwargs):
                with self.get_context(instance):
                    self.start(instance, *args, **kwargs)
                    result = self.func(instance, *args, **kwargs)
                    self.stop(instance, *args, **kwargs)
                    return result

            return sync_wrapper

    def get_context(self, instance):
        """

        If the instance has a context attribute, use that - otherwise use a null context.

        """
        context = getattr(instance, self.CONTEXT_KEY, None)
        if context:
            return context
        return context_tools.null()

    def start(self, instance, *args, **kwargs):
        pass

    def stop(self, instance, *args, **kwargs):
        pass
