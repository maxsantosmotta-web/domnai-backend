from app.domnai_core.shadow_results import ShadowApprovalCriteria, evaluate_shadow_results
from app.domnai_core.shadow_validation import BEHAVIOR_EVALUATION_VERSION, ShadowComparison


def comparison(*, passed: bool, score: float = 1.0, similarity: float = 0.0) -> ShadowComparison:
    return ShadowComparison(
        request_id=f"req-{passed}-{score}-{similarity}",
        legacy_provider="legacy",
        candidate_provider="core",
        legacy_length=20,
        candidate_length=40,
        similarity_ratio=similarity,
        candidate_empty=False,
        behavior_score=score,
        behavior_passed=passed,
        behavior_version=BEHAVIOR_EVALUATION_VERSION,
    )


def test_legacy_similarity_does_not_block_behavioral_approval():
    items = tuple(comparison(passed=True, similarity=0.0) for _ in range(100))
    report = evaluate_shadow_results(items)
    assert report.average_similarity == 0.0
    assert report.behavior_adherence_rate == 1.0
    assert report.approved is True


def test_behavioral_approval_requires_one_hundred_percent_adherence():
    items = tuple(comparison(passed=True) for _ in range(99)) + (
        comparison(passed=False, score=0.8571),
    )
    report = evaluate_shadow_results(items)
    assert report.behavior_adherence_rate == 0.99
    assert report.approved is False


def test_old_unversioned_samples_are_not_mixed_with_behavioral_samples():
    old = ShadowComparison(
        request_id="old",
        legacy_provider="legacy",
        candidate_provider="core",
        legacy_length=10,
        candidate_length=10,
        similarity_ratio=1.0,
        candidate_empty=False,
    )
    current = tuple(comparison(passed=True) for _ in range(3))
    report = evaluate_shadow_results(
        (old,) + current,
        criteria=ShadowApprovalCriteria(minimum_samples=3),
    )
    assert report.sample_count == 3
    assert report.approved is True
