from pathlib import Path


def test_worker_never_claims_generated_tasks():
    source = Path("app/services/chat_task_worker.py").read_text(encoding="utf-8")
    assert '.where(ChatTask.status == "queued")' in source
    assert 'status.in_(["queued", "generated"])' not in source
    assert 'task.status = "generated"' not in source


def test_credit_account_is_locked_before_idempotency_lookup():
    source = Path("app/services/credit_meter.py").read_text(encoding="utf-8")
    lock = source.index(".with_for_update()")
    lookup = source.index("CreditTransaction.stripe_event_id == idempotency_key")
    assert lock < lookup
