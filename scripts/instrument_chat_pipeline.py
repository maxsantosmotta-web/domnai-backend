from pathlib import Path

path = Path('/app/app/services/chat_task_worker.py')
source = path.read_text(encoding='utf-8')

if 'def _elapsed_ms(started_at: float) -> int:' not in source:
    source = source.replace(
        'def _now():\n    return datetime.now(timezone.utc)\n',
        'def _now():\n    return datetime.now(timezone.utc)\n\n\ndef _elapsed_ms(started_at: float) -> int:\n    return max(0, round((time.perf_counter() - started_at) * 1000))\n',
        1,
    )

source = source.replace(
    'def _process_task(task_id: str) -> None:\n    with session_scope() as db:',
    'def _process_task(task_id: str) -> None:\n    task_started_at = time.perf_counter()\n    timings: dict[str, int] = {}\n    with session_scope() as db:',
    1,
)

source = source.replace(
    '        existing_result = json.loads(task.result_json) if task.result_json else None\n        user_id = task.user_id\n',
    '        existing_result = json.loads(task.result_json) if task.result_json else None\n        user_id = task.user_id\n        created_at = task.created_at\n\n    if created_at is not None:\n        try:\n            created_utc = created_at if created_at.tzinfo else created_at.replace(tzinfo=timezone.utc)\n            timings["queue_ms"] = max(0, round((_now() - created_utc).total_seconds() * 1000))\n        except Exception:\n            pass\n',
    1,
)

source = source.replace(
    '    if existing_result is None:\n        ensure_minimum_credit(user_id)',
    '    if existing_result is None:\n        preparation_started_at = time.perf_counter()\n        ensure_minimum_credit(user_id)',
    1,
)

source = source.replace(
    '        diagnosis_state = load_diagnosis_state(user_id, operation)\n        sources: list[dict] = []',
    '        diagnosis_state = load_diagnosis_state(user_id, operation)\n        timings["preparation_ms"] = _elapsed_ms(preparation_started_at)\n        sources: list[dict] = []',
    1,
)

source = source.replace(
    '        if should_research_web(original_message, operation):\n            research = research_web(original_message)',
    '        if should_research_web(original_message, operation):\n            research_started_at = time.perf_counter()\n            research = research_web(original_message)\n            timings["research_ms"] = _elapsed_ms(research_started_at)',
    1,
)

source = source.replace(
    '        result = generate_orchestrated_response(\n',
    '        intelligence_started_at = time.perf_counter()\n        result = generate_orchestrated_response(\n',
    1,
)

source = source.replace(
    '            diagnosis_state=diagnosis_state,\n        )\n        reply = result.text',
    '            diagnosis_state=diagnosis_state,\n        )\n        timings["intelligence_ms"] = _elapsed_ms(intelligence_started_at)\n        reply = result.text',
    1,
)

source = source.replace(
    '        artifacts: list[dict] = []\n        decision = decide_artifact(',
    '        artifacts: list[dict] = []\n        artifact_started_at = time.perf_counter()\n        decision = decide_artifact(',
    1,
)

source = source.replace(
    '        existing_result = {\n            "reply": reply,',
    '        timings["artifact_ms"] = _elapsed_ms(artifact_started_at)\n        timings["generation_total_ms"] = _elapsed_ms(task_started_at)\n        existing_result = {\n            "reply": reply,',
    1,
)

source = source.replace(
    '            "sources": sources,\n        }',
    '            "sources": sources,\n            "timings": timings,\n        }',
    1,
)

source = source.replace(
    '    usage = charge_usage(user_id, meter_result, idempotency_key=f"chat-task:{task_id}")',
    '    billing_started_at = time.perf_counter()\n    usage = charge_usage(user_id, meter_result, idempotency_key=f"chat-task:{task_id}")\n    timings = dict(existing_result.get("timings") or timings)\n    timings["billing_ms"] = _elapsed_ms(billing_started_at)',
    1,
)

source = source.replace(
    '    existing_result["usage"] = usage\n    _append_completed_response(',
    '    existing_result["usage"] = usage\n    persistence_started_at = time.perf_counter()\n    _append_completed_response(',
    1,
)

source = source.replace(
    '    with session_scope() as db:\n        task = db.get(ChatTask, task_id)\n        if task is None:\n            return\n        task.result_json = json.dumps(existing_result, ensure_ascii=False)\n        task.status = "completed"',
    '    timings["persistence_ms"] = _elapsed_ms(persistence_started_at)\n    timings["total_ms"] = _elapsed_ms(task_started_at)\n    existing_result["timings"] = timings\n    with session_scope() as db:\n        task = db.get(ChatTask, task_id)\n        if task is None:\n            return\n        task.result_json = json.dumps(existing_result, ensure_ascii=False)\n        task.status = "completed"',
    1,
)

required = (
    '"queue_ms"',
    '"preparation_ms"',
    '"intelligence_ms"',
    '"artifact_ms"',
    '"billing_ms"',
    '"persistence_ms"',
    '"total_ms"',
)
missing = [marker for marker in required if marker not in source]
if missing:
    raise RuntimeError(f'Instrumentação incompleta: {missing}')

path.write_text(source, encoding='utf-8')
