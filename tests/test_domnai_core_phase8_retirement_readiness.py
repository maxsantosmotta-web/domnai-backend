from datetime import datetime, timezone

from app.domnai_core.retirement_readiness import (
    LegacyRetirementCriteria,
    evaluate_legacy_retirement,
)


def test_retirement_is_blocked_without_full_cutover(monkeypatch):
    monkeypatch.delenv("DOMNAI_LEGACY_RETIREMENT_CONFIRMED", raising=False)
    monkeypatch.delenv("DOMNAI_FULL_CUTOVER_STARTED_AT", raising=False)
    report = evaluate_legacy_retirement(
        summary={"sampleCount": 1000, "newCoreResponses": 1000, "fallbackRate": 0.0},
        cutover_enabled=False,
        traffic_percent=0,
        fallback_enabled=True,
    )
    assert report.ready is False
    assert "cutover_disabled" in report.blockers
    assert "traffic_not_100_percent" in report.blockers


def test_retirement_requires_stability_and_confirmation(monkeypatch):
    monkeypatch.setenv("DOMNAI_FULL_CUTOVER_STARTED_AT", "2026-07-19T00:00:00Z")
    monkeypatch.setenv("DOMNAI_LEGACY_RETIREMENT_CONFIRMED", "true")
    report = evaluate_legacy_retirement(
        summary={"sampleCount": 500, "newCoreResponses": 499, "fallbackRate": 0.002},
        cutover_enabled=True,
        traffic_percent=100,
        fallback_enabled=True,
        now=datetime(2026, 7, 20, 1, 0, tzinfo=timezone.utc),
    )
    assert report.ready is True
    assert report.blockers == ()


def test_retirement_rejects_high_fallback_rate(monkeypatch):
    monkeypatch.setenv("DOMNAI_FULL_CUTOVER_STARTED_AT", "2026-07-18T00:00:00Z")
    monkeypatch.setenv("DOMNAI_LEGACY_RETIREMENT_CONFIRMED", "true")
    report = evaluate_legacy_retirement(
        summary={"sampleCount": 1000, "newCoreResponses": 970, "fallbackRate": 0.03},
        cutover_enabled=True,
        traffic_percent=100,
        fallback_enabled=True,
        criteria=LegacyRetirementCriteria(),
        now=datetime(2026, 7, 20, 1, 0, tzinfo=timezone.utc),
    )
    assert report.ready is False
    assert "new_core_rate_below_threshold" in report.blockers
    assert "fallback_rate_above_threshold" in report.blockers
