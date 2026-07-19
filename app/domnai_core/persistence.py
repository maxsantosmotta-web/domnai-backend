from __future__ import annotations

from dataclasses import dataclass
from threading import RLock
from typing import Protocol

from app.domnai_core.contracts import ConversationRequest, ConversationResponse


@dataclass(frozen=True, slots=True)
class ConversationRecord:
    conversation_id: str
    request: ConversationRequest
    response: ConversationResponse


class ConversationRepository(Protocol):
    def append(self, record: ConversationRecord) -> None:
        ...


class NullConversationRepository:
    def append(self, record: ConversationRecord) -> None:
        return None


class InMemoryConversationRepository:
    """Persistência temporária sem dependência do banco legado."""

    def __init__(self) -> None:
        self._records: list[ConversationRecord] = []
        self._lock = RLock()

    def append(self, record: ConversationRecord) -> None:
        with self._lock:
            self._records.append(record)

    def records(self) -> tuple[ConversationRecord, ...]:
        with self._lock:
            return tuple(self._records)
