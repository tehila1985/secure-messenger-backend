"""
broadcaster.py — In-process SSE pub/sub for real-time message delivery.

Design:
  - Each authenticated user gets a named set of asyncio.Queue instances
    (one per open /stream connection, supporting multiple tabs/devices).
  - publish() fans out to every queue of the target user, or to all users
    when target_user is None (broadcast mode).
  - _Subscription is an async context manager so callers cannot forget to
    unregister — the cleanup is guaranteed even on client disconnect.
"""

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator


class Broadcaster:
    def __init__(self) -> None:
        self._subscribers: dict[str, set[asyncio.Queue[dict]]] = {}

    def subscribe(self, username: str) -> "_Subscription":
        return _Subscription(self, username)

    async def publish(self, message: dict, target_user: str | None = None) -> None:
        if target_user:
            queues = self._subscribers.get(target_user, set())
            for queue in queues:
                await queue.put(message)
        else:
            for queues in self._subscribers.values():
                for queue in queues:
                    await queue.put(message)

    # ------------------------------------------------------------------
    # Internals used only by _Subscription
    # ------------------------------------------------------------------

    def _register(self, username: str, queue: "asyncio.Queue[dict]") -> None:
        self._subscribers.setdefault(username, set()).add(queue)

    def _unregister(self, username: str, queue: "asyncio.Queue[dict]") -> None:
        bucket = self._subscribers.get(username)
        if bucket:
            bucket.discard(queue)
            if not bucket:
                del self._subscribers[username]


class _Subscription:
    """Async context manager that registers/unregisters a per-user queue."""

    def __init__(self, broadcaster: Broadcaster, username: str) -> None:
        self._broadcaster = broadcaster
        self._username = username
        self._queue: asyncio.Queue[dict] = asyncio.Queue()

    async def __aenter__(self) -> "asyncio.Queue[dict]":
        self._broadcaster._register(self._username, self._queue)
        return self._queue

    async def __aexit__(self, *_) -> None:
        self._broadcaster._unregister(self._username, self._queue)


broadcaster = Broadcaster()
