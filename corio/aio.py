import asyncio
import inspect


def ensure_loop():
    """

    Ensures a loop has been started in the current thread.

    """
    try:
        return asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop


is_async = inspect.iscoroutinefunction
