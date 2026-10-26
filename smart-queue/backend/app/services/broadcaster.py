import asyncio
from typing import Dict, Set
from uuid import UUID

class LiveBroadcaster:
    """
    Step 9 In-Memory Asynchronous Pub/Sub Broadcaster for Live WebSockets / SSE.
    Enables zero-latency streaming of queue transitions, call-outs, and notifications.
    """
    def __init__(self):
        # user_id -> set of asyncio.Queue
        self._user_listeners: Dict[str, Set[asyncio.Queue]] = {}
        # branch_id -> set of asyncio.Queue
        self._branch_listeners: Dict[str, Set[asyncio.Queue]] = {}

    def subscribe_user(self, user_id: str) -> asyncio.Queue:
        q = asyncio.Queue()
        if user_id not in self._user_listeners:
            self._user_listeners[user_id] = set()
        self._user_listeners[user_id].add(q)
        return q

    def unsubscribe_user(self, user_id: str, q: asyncio.Queue):
        if user_id in self._user_listeners:
            self._user_listeners[user_id].discard(q)
            if not self._user_listeners[user_id]:
                del self._user_listeners[user_id]

    def subscribe_branch(self, branch_id: str) -> asyncio.Queue:
        q = asyncio.Queue()
        if branch_id not in self._branch_listeners:
            self._branch_listeners[branch_id] = set()
        self._branch_listeners[branch_id].add(q)
        return q

    def unsubscribe_branch(self, branch_id: str, q: asyncio.Queue):
        if branch_id in self._branch_listeners:
            self._branch_listeners[branch_id].discard(q)
            if not self._branch_listeners[branch_id]:
                del self._branch_listeners[branch_id]

    async def broadcast_to_user(self, user_id: str, data: dict):
        listeners = self._user_listeners.get(str(user_id), set())
        for q in list(listeners):
            try:
                await q.put(data)
            except Exception:
                pass

    async def broadcast_to_branch(self, branch_id: str, data: dict):
        listeners = self._branch_listeners.get(str(branch_id), set())
        for q in list(listeners):
            try:
                await q.put(data)
            except Exception:
                pass

    def broadcast_sync_user(self, user_id: str, data: dict):
        listeners = self._user_listeners.get(str(user_id), set())
        for q in list(listeners):
            try:
                q.put_nowait(data)
            except Exception:
                pass

    def broadcast_sync_branch(self, branch_id: str, data: dict):
        listeners = self._branch_listeners.get(str(branch_id), set())
        for q in list(listeners):
            try:
                q.put_nowait(data)
            except Exception:
                pass

broadcaster = LiveBroadcaster()
