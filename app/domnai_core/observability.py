from __future__ import annotations

from dataclasses import dataclass
from threading import RLock
from time import monotonic
from typing import Protocol


@dataclass(frozen=True, slots=True)
class CoreRequestMetric:
    outcome: str
    duration_ms: int
    provider: str | None = None
    model: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    tool_iterations: int = 0


class CoreMetricsSink(Protocol):
    def record(self, metric: CoreRequestMetric) -> None:
        ...


class NullCoreMetricsSink:
    def record(self, metric: CoreRequestMetric) -> None:
        return None


class InMemoryCoreMetricsSink:
    def __init__(self) -> None:
        self._items: list[CoreRequestMetric] = []
        self._lock = RLock()

    def record(self, metric: CoreRequestMetric) -> None:
        with self._lock:
            self._items.append(metric)

    def items(self) -> tuple[CoreRequestMetric, ...]:
        with self._lock:
            return tuple(self._items)


class RequestTimer:
    def __init__(self) -> None:
        self._started_at = monotonic()

    def elapsed_ms(self) -> int:
        return max(0, int((monotonic() - self._started_at) * 1000))
