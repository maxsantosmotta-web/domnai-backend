from __future__ import annotations

from dataclasses import asdict, dataclass
from threading import RLock
from typing import Protocol

from sqlalchemy import text

from app.database import session_scope
from app.domnai_core.shadow_validation import ShadowComparison


@dataclass(frozen=True, slots=True)
class ShadowApprovalCriteria:
    minimum_samples: int = 100
    minimum_success_rate: float = 0.98
    minimum_non_empty_rate: float = 0.99
    minimum_average_similarity: float = 0.35


@dataclass(frozen=True, slots=True)
class ShadowApprovalReport:
    sample_count: int
    success_rate: float
    non_empty_rate: float
    average_similarity: float
    approved: bool

    def as_dict(self) -> dict:
        return asdict(self)


class ShadowResultStore(Protocol):
    def save(self, comparison: ShadowComparison) -> None:
        ...

    def recent(self, *, limit: int = 100) -> tuple[ShadowComparison, ...]:
        ...


class InMemoryShadowResultStore:
    def __init__(self) -> None:
        self._items: list[ShadowComparison] = []
        self._lock = RLock()

    def save(self, comparison: ShadowComparison) -> None:
        with self._lock:
            self._items.append(comparison)

    def recent(self, *, limit: int = 100) -> tuple[ShadowComparison, ...]:
        safe_limit = max(1, min(int(limit), 1000))
        with self._lock:
            return tuple(reversed(self._items[-safe_limit:]))


class PostgresShadowResultStore:
    TABLE = "domnai_shadow_comparisons"

    def ensure_schema(self) -> None:
        with session_scope() as db:
            db.execute(text(f"""
                CREATE TABLE IF NOT EXISTS {self.TABLE} (
                    id BIGSERIAL PRIMARY KEY,
                    request_id VARCHAR(128) NOT NULL,
                    legacy_provider VARCHAR(100) NOT NULL,
                    candidate_provider VARCHAR(100) NOT NULL,
                    legacy_length INTEGER NOT NULL,
                    candidate_length INTEGER NOT NULL,
                    similarity_ratio DOUBLE PRECISION NOT NULL,
                    candidate_empty BOOLEAN NOT NULL,
                    candidate_error VARCHAR(200) NOT NULL DEFAULT '',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """))
            db.execute(text(f"CREATE INDEX IF NOT EXISTS idx_{self.TABLE}_created ON {self.TABLE} (created_at DESC)"))

    def save(self, comparison: ShadowComparison) -> None:
        with session_scope() as db:
            db.execute(text(f"""
                INSERT INTO {self.TABLE} (
                    request_id, legacy_provider, candidate_provider,
                    legacy_length, candidate_length, similarity_ratio,
                    candidate_empty, candidate_error
                ) VALUES (
                    :request_id, :legacy_provider, :candidate_provider,
                    :legacy_length, :candidate_length, :similarity_ratio,
                    :candidate_empty, :candidate_error
                )
            """), comparison.as_safe_dict())

    def recent(self, *, limit: int = 100) -> tuple[ShadowComparison, ...]:
        safe_limit = max(1, min(int(limit), 1000))
        with session_scope() as db:
            rows = db.execute(text(f"""
                SELECT request_id, legacy_provider, candidate_provider,
                       legacy_length, candidate_length, similarity_ratio,
                       candidate_empty, candidate_error
                FROM {self.TABLE}
                ORDER BY created_at DESC
                LIMIT :limit
            """), {"limit": safe_limit}).mappings().all()
        return tuple(ShadowComparison(**dict(row)) for row in rows)


class PersistingShadowComparisonSink:
    def __init__(self, store: ShadowResultStore) -> None:
        self._store = store

    def record(self, comparison: ShadowComparison) -> None:
        self._store.save(comparison)


def evaluate_shadow_results(
    comparisons: tuple[ShadowComparison, ...],
    *,
    criteria: ShadowApprovalCriteria | None = None,
) -> ShadowApprovalReport:
    resolved = criteria or ShadowApprovalCriteria()
    total = len(comparisons)
    if total == 0:
        return ShadowApprovalReport(0, 0.0, 0.0, 0.0, False)
    successes = sum(1 for item in comparisons if not item.candidate_error)
    non_empty = sum(1 for item in comparisons if not item.candidate_empty)
    average_similarity = sum(item.similarity_ratio for item in comparisons) / total
    success_rate = successes / total
    non_empty_rate = non_empty / total
    approved = bool(
        total >= resolved.minimum_samples
        and success_rate >= resolved.minimum_success_rate
        and non_empty_rate >= resolved.minimum_non_empty_rate
        and average_similarity >= resolved.minimum_average_similarity
    )
    return ShadowApprovalReport(
        sample_count=total,
        success_rate=round(success_rate, 4),
        non_empty_rate=round(non_empty_rate, 4),
        average_similarity=round(average_similarity, 4),
        approved=approved,
    )
