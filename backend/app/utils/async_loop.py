# backend/app/utils/async_loop.py
"""
Async event loop bridge for use in synchronous Flask threads.

Graphiti is fully async. Flask is fully sync. This module maintains
a single asyncio event loop running in a dedicated daemon thread.
All Flask threads share this loop via run_coroutine_threadsafe(),
which is thread-safe by design.

Usage:
    from app.utils.async_loop import run_async
    result = run_async(some_coroutine(args))
"""

import asyncio
import threading
from typing import TypeVar, Coroutine, Any

T = TypeVar("T")

_loop: asyncio.AbstractEventLoop | None = None
_loop_thread: threading.Thread | None = None
_lock = threading.Lock()


def get_loop() -> asyncio.AbstractEventLoop:
    """Return the shared event loop, creating it if needed."""
    global _loop, _loop_thread
    with _lock:
        if _loop is None or _loop.is_closed():
            _loop = asyncio.new_event_loop()
            _loop_thread = threading.Thread(
                target=_loop.run_forever,
                name="graphiti-async-loop",
                daemon=True,
            )
            _loop_thread.start()
    return _loop


def run_async(coro: Coroutine[Any, Any, T]) -> T:
    """
    Run an async coroutine from synchronous code.
    Blocks until the coroutine completes. Thread-safe.
    """
    future = asyncio.run_coroutine_threadsafe(coro, get_loop())
    return future.result()
