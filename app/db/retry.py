"""
Retry helper for Supabase/httpx calls.

Wraps transient network errors (httpx.ReadError, httpx.ConnectError, etc.)
with exponential backoff so a burst of WhatsApp webhooks doesn't cascade into
500s when the Supabase connection pool hiccups.
"""

import time
import logging
import functools
from typing import TypeVar, Callable, Optional

import httpx

logger = logging.getLogger(__name__)

T = TypeVar("T")

# Exceptions considered transient and worth retrying
_TRANSIENT_EXCEPTIONS = (
    httpx.ReadError,
    httpx.ConnectError,
    httpx.RemoteProtocolError,
    httpx.ReadTimeout,
    httpx.ConnectTimeout,
    ConnectionError,
    OSError,
)


def with_retry(
    fn: Optional[Callable[..., T]] = None,
    *,
    max_retries: int = 3,
    base_delay: float = 0.3,
    max_delay: float = 2.0,
) -> Callable[..., T]:
    """
    Decorator / wrapper that retries on transient httpx errors.

    Usage as decorator:
        @with_retry
        def fetch_data(): ...

        @with_retry(max_retries=5)
        def fetch_data(): ...

    Usage inline:
        result = with_retry(lambda: db.table("x").select("*").execute())
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exc = None
            for attempt in range(1, max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except _TRANSIENT_EXCEPTIONS as exc:
                    last_exc = exc
                    if attempt < max_retries:
                        delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
                        logger.warning(
                            "[retry] %s attempt %d/%d failed (%s: %s), "
                            "retrying in %.1fs…",
                            func.__name__ if hasattr(func, "__name__") else "call",
                            attempt,
                            max_retries,
                            type(exc).__name__,
                            exc,
                            delay,
                        )
                        time.sleep(delay)
                    else:
                        logger.error(
                            "[retry] %s exhausted %d retries – propagating %s",
                            func.__name__ if hasattr(func, "__name__") else "call",
                            max_retries,
                            type(exc).__name__,
                        )
            raise last_exc  # type: ignore[misc]

        return wrapper

    # Handle both @with_retry and @with_retry(...)
    if fn is not None:
        return decorator(fn)
    return decorator
