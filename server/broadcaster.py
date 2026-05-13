import asyncio
from typing import Dict, Set

class Broadcaster:
    def __init__(self):
        self.subscribers: Dict[str, Set[asyncio.Queue]] = {}

    def subscribe(self, username: str):
        return _Subscription(self, username)

    async def publish(self, message: dict, target_user: str = None):
        if target_user:
            for queue in self.subscribers.get(target_user, []):
                await queue.put(message)
        else:
            for user_queues in self.subscribers.values():
                for queue in user_queues:
                    await queue.put(message)


class _Subscription:
    def __init__(self, broadcaster: "Broadcaster", username: str):
        self._broadcaster = broadcaster
        self._username = username
        self._queue = asyncio.Queue()

    async def __aenter__(self):
        subs = self._broadcaster.subscribers
        if self._username not in subs:
            subs[self._username] = set()
        subs[self._username].add(self._queue)
        return self._queue

    async def __aexit__(self, *_):
        subs = self._broadcaster.subscribers
        subs[self._username].discard(self._queue)
        if not subs[self._username]:
            del subs[self._username]


broadcaster = Broadcaster()