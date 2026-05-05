from contextlib import contextmanager, ExitStack


@contextmanager
def null():
    """

    Null context manager.

    """
    yield


@contextmanager
def contexts(*contexts):
    """

    Tee context managers.

    """
    with ExitStack() as stack:
        resources = [stack.enter_context(context) for context in contexts]
        yield resources
