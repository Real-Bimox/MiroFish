# backend/tests/test_async_loop.py
import asyncio
import threading
from app.utils.async_loop import run_async, get_loop


async def _add(a, b):
    await asyncio.sleep(0)
    return a + b


def test_run_async_returns_result():
    assert run_async(_add(2, 3)) == 5


def test_run_async_is_thread_safe():
    results = []

    def worker():
        results.append(run_async(_add(10, 10)))

    threads = [threading.Thread(target=worker) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert results == [20] * 10


def test_same_loop_reused():
    loop1 = get_loop()
    loop2 = get_loop()
    assert loop1 is loop2
