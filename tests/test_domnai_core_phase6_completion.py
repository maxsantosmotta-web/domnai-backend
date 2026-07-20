from app.domnai_core.shadow_results import (
    InMemoryShadowResultStore,
    ShadowApprovalCriteria,
    evaluate_shadow_results,
)
from app.domnai_core.shadow_validation import (
    BEHAVIOR_EVALUATION_VERSION,
    ShadowComparison,
    ShadowValidationSettings,
)
from app.services.shadow_validation_worker import start_shadow_validation_worker


def _comparison(*, similarity=0.8, empty=False, error="", behavior_passed=True, behavior_score=1.0):
    return ShadowComparison(
        request_id="req",
        legacy_provider="legacy",
        candidate_provider="candidate" if not error else "error",
        legacy_length=100,
        candidate_length=90 if not empty else 0,
        similarity_ratio=similarity,
        candidate_empty=empty,
        candidate_error=error,
        behavior_score=behavior_score,
        behavior_passed=behavior_passed,
        behavior_version=BEHAVIOR_EVALUATION_VERSION,
    )


def test_store_keeps_only_safe_comparison_fields():
    store = InMemoryShadowResultStore()
    store.save(_comparison())
    item = store.recent(limit=1)[0]
    payload = item.as_safe_dict()
    assert "prompt" not in payload
    assert "response" not in payload
    assert payload["similarity_ratio"] == 0.8
    assert payload["behavior_score"] == 1.0


def test_approval_requires_minimum_samples_and_full_behavioral_adherence():
    criteria = ShadowApprovalCriteria(
        minimum_samples=3,
        minimum_success_rate=1.0,
        minimum_non_empty_rate=1.0,
        minimum_behavior_adherence_rate=1.0,
    )
    insufficient = evaluate_shadow_results((_comparison(), _comparison()), criteria=criteria)
    assert insufficient.approved is False
    approved = evaluate_shadow_results(
        (_comparison(similarity=0.0), _comparison(similarity=0.2), _comparison(similarity=0.9)),
        criteria=criteria,
    )
    assert approved.approved is True
    assert approved.sample_count == 3
    assert approved.behavior_adherence_rate == 1.0


def test_approval_rejects_candidate_errors_empty_responses_and_partial_behavior():
    criteria = ShadowApprovalCriteria(
        minimum_samples=2,
        minimum_success_rate=1.0,
        minimum_non_empty_rate=1.0,
        minimum_behavior_adherence_rate=1.0,
    )
    report = evaluate_shadow_results(
        (
            _comparison(error="TimeoutError", empty=True, similarity=0.0, behavior_passed=False, behavior_score=0.0),
            _comparison(),
        ),
        criteria=criteria,
    )
    assert report.approved is False
    assert report.success_rate == 0.5
    assert report.non_empty_rate == 0.5
    assert report.behavior_adherence_rate == 0.5


def test_shadow_worker_is_not_started_when_feature_flag_is_off(monkeypatch):
    monkeypatch.setenv("DOMNAI_SHADOW_VALIDATION_ENABLED", "false")
    monkeypatch.setenv("DOMNAI_SHADOW_SAMPLE_PERCENT", "0")
    assert start_shadow_validation_worker() is False


def test_shadow_settings_keep_rollback_off_by_default(monkeypatch):
    monkeypatch.delenv("DOMNAI_SHADOW_VALIDATION_ENABLED", raising=False)
    monkeypatch.delenv("DOMNAI_SHADOW_SAMPLE_PERCENT", raising=False)
    settings = ShadowValidationSettings.from_env()
    assert settings.enabled is False
    assert settings.selects("any") is False
