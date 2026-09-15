"""Reusable timing decorator and context manager."""

from __future__ import annotations

from contextlib import contextmanager
from functools import wraps
import inspect
import logging
from time import perf_counter
from typing import Any, Callable, Iterator, TypeVar, cast

from .logging_config import get_logger


F = TypeVar("F", bound=Callable[..., Any])


@contextmanager
def timed_operation(
    operation: str,
    *,
    logger: logging.Logger | None = None,
    level: int = logging.INFO,
) -> Iterator[None]:
    """Log start, successful completion, failure, and duration for an operation."""
    active_logger = logger or get_logger(stage="pipeline")
    started = perf_counter()
    active_logger.log(level, "Started operation=%s", operation)
    try:
        yield
    except Exception:
        active_logger.exception(
            "Failed operation=%s duration_seconds=%.3f",
            operation,
            perf_counter() - started,
        )
        raise
    else:
        active_logger.log(
            level,
            "Completed operation=%s duration_seconds=%.3f",
            operation,
            perf_counter() - started,
        )


def timed(
    function: F | None = None,
    *,
    logger: logging.Logger | None = None,
    level: int = logging.INFO,
) -> Callable[[F], F] | F:
    """Decorate sync or async functions with execution timing logs."""
    def decorator(func: F) -> F:
        active_logger = logger or get_logger(func.__module__)
        if inspect.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                with timed_operation(func.__qualname__, logger=active_logger, level=level):
                    return await func(*args, **kwargs)

            return cast(F, async_wrapper)

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            with timed_operation(func.__qualname__, logger=active_logger, level=level):
                return func(*args, **kwargs)

        return cast(F, wrapper)

    return decorator(function) if function is not None else decorator


__all__ = ["timed", "timed_operation"]
