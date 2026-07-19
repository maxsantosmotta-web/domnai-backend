from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone

_TRUE_VALUES = {"1", "true", "yes", "on"}


@dataclass(frozen=True, slots=True)
class LegacyRetirementCriteria:
    minimum_samples: int = 500
    maximum_fallback_rate: float = 0.01
    minimum_new_core_rate: float = 0.99
    minimum_stability_hours: int = 24


@dataclass(frozen=True, slots=True)
class LegacyRetirementReport:
    sample_count: int
    new_core_rate: float
    fallback_rate: float
    traffic_percent: int
    cutover_enabled: bool
    fallback_enabled: bool
    stability_hours: float
    explicit_confirmation: bool
    ready: bool
    blockers: tuple[str, ...]

    def as_dict(self) -> dict:
        data = asdict(self)
        data["blockers"] = list(self.blockers)
        return data


def _stability_hours_from_env(now: datetime | None = None) -> float:
    raw = os.getenv("DOMNAI_FULL_CUTOVER_STARTED_AT", "").strip()
    if not raw:
        return 0.0
    try:
        started = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return 0.0
    if started.tzinfo is None:
        started = started.replace(tzinfo=timezone.utc)
    current = now or datetime.now(timezone.utc)
    return max(0.0, (current.astimezone(timezone.utc) - started.astimezone(timezone.utc)).total_seconds() / 3600)


def evaluate_legacy_retirement(
    *,
    summary: dict,
    cutover_enabled: bool,
    traffic_percent: int,
    fallback_enabled: bool,
    criteria: LegacyRetirementCriteria | None = None,
    now: datetime | None = None,
) -> LegacyRetirementReport:
    resolved = criteria or LegacyRetirementCriteria()
    samples = max(0, int(summary.get("sampleCount") or 0))
    new_core = max(0, int(summary.get("newCoreResponses") or 0))
    fallback_rate = max(0.0, float(summary.get("fallbackRate") or 0.0))
    new_core_rate = (new_core / samples) if samples else 0.0
    stability_hours = _stability_hours_from_env(now)
    explicit_confirmation = (
        os.getenv("DOMNAI_LEGACY_RETIREMENT_CONFIRMED", "false").strip().lower() in _TRUE_VALUES
    )

    blockers: list[str] = []
    if not cutover_enabled:
        blockers.append("cutover_disabled")
    if traffic_percent != 100:
        blockers.append("traffic_not_100_percent")
    if not fallback_enabled:
        blockers.append("fallback_must_remain_enabled_during_validation")
    if samples < resolved.minimum_samples:
        blockers.append("insufficient_samples")
    if new_core_rate < resolved.minimum_new_core_rate:
        blockers.append("new_core_rate_below_threshold")
    if fallback_rate > resolved.maximum_fallback_rate:
        blockers.append("fallback_rate_above_threshold")
    if stability_hours < resolved.minimum_stability_hours:
        blockers.append("stability_window_incomplete")
    if not explicit_confirmation:
        blockers.append("explicit_confirmation_missing")

    return LegacyRetirementReport(
        sample_count=samples,
        new_core_rate=round(new_core_rate, 4),
        fallback_rate=round(fallback_rate, 4),
        traffic_percent=traffic_percent,
        cutover_enabled=cutover_enabled,
        fallback_enabled=fallback_enabled,
        stability_hours=round(stability_hours, 2),
        explicit_confirmation=explicit_confirmation,
        ready=not blockers,
        blockers=tuple(blockers),
    )
