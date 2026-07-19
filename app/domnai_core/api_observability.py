from __future__ import annotations

from dataclasses import asdict, dataclass
from threading import RLock
from time import perf_counter
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ApiRequestEvent:
    request_id: str
    route: str
    method: str
    status_code: int
    duration_ms: float
    subject: str = ""
    conversation_id: str = ""
    error_type: str = ""

    def as_dict(self) -> dict:
        return asdict(self)


class ApiEventSink(Protocol):
    def record(self, event: ApiRequestEvent) -> None:
        ...


class NullApiEventSink:
    def record(self, event: ApiRequestEvent) -> None:
        return None


class InMemoryApiEventSink:
    def __init__(self) -> None:
        self._items: list[ApiRequestEvent] = []
        self._lock = RLock()

    def record(self, event: ApiRequestEvent) -> None:
        with self._lock:
            self._items.append(event)

    def items(self) -> tuple[ApiRequestEvent, ...]:
        with self._lock:
            return tuple(self._items)


class ApiRequestTimer:
    def __init__(self) -> None:
        self._started = perf_counter()

    def elapsed_ms(self) -> float:
        return round(max(0.0, (perf_counter() - self._started) * 1000), 3)
