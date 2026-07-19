from __future__ import annotations

from copy import deepcopy
from threading import RLock
from typing import Protocol


class MemoryStore(Protocol):
    def load(self, conversation_id: str) -> dict:
        ...

    def save(self, conversation_id: str, memory: dict) -> None:
        ...


class NullMemoryStore:
    def load(self, conversation_id: str) -> dict:
        return {}

    def save(self, conversation_id: str, memory: dict) -> None:
        return None


class InMemoryMemoryStore:
    """Implementação temporária e isolada para desenvolvimento do novo núcleo."""

    def __init__(self) -> None:
        self._items: dict[str, dict] = {}
        self._lock = RLock()

    def load(self, conversation_id: str) -> dict:
        with self._lock:
            return deepcopy(self._items.get(conversation_id, {}))

    def save(self, conversation_id: str, memory: dict) -> None:
        with self._lock:
            self._items[conversation_id] = deepcopy(memory)
