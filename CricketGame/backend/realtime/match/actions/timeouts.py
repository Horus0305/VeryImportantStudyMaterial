"""Timeout helpers — kept minimal after removing ball-pick timers."""


def _cancel_timeout(room, key: str) -> None:
    task = room.pending_timeouts.pop(key, None)
    if task and not task.done():
        task.cancel()


def _start_timeout(room, key: str, coro) -> None:
    import asyncio
    _cancel_timeout(room, key)
    room.pending_timeouts[key] = asyncio.create_task(coro)
