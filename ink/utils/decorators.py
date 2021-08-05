import functools
import asyncio

__all__ = ("asyncexe",)

# obv ty bobo
def asyncexe(executor=None):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            partial = functools.partial(func, *args, **kwargs)
            loop = asyncio.get_event_loop()
            return loop.run_in_executor(executor, partial)

        return wrapper

    return decorator
