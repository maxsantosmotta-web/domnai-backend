from pathlib import Path

worker_path = Path('/app/app/services/chat_task_worker.py')
worker = worker_path.read_text(encoding='utf-8')

if 'def _elapsed_ms(started_at: float) -> int:' not in worker:
    worker = worker.replace(
        'def _now():\n    return datetime.now(timezone.utc)\n',
        'def _now():\n    return datetime.now(timezone.utc)\n\n\ndef _elapsed_ms(started_at: float) -> int:\n    return max(0, round((time.perf_counter() - started_at) * 1000))\n',
        1,
    )

worker = worker.replace(
    'def _process_task(task_id: str) -> None:\n    with session_scope() as db:',
    'def _process_task(task_id: str) -> None:\n    task_started_at = time.perf_counter()\n    timings: dict[str, int] = {}\n    with session_scope() as db:',
    1,
)

worker = worker.replace(
    '        existing_result = json.loads(task.result_json) if task.result_json else None\n        user_id = task.user_id\n',
    '        existing_result = json.loads(task.result_json) if task.result_json else None\n        user_id = task.user_id\n        created_at = task.created_at\n\n    if created_at is not None:\n        try:\n            created_utc = created_at if created_at.tzinfo else created_at.replace(tzinfo=timezone.utc)\n            timings["queue_ms"] = max(0, round((_now() - created_utc).total_seconds() * 1000))\n        except Exception:\n            pass\n',
    1,
)

worker = worker.replace(
    '    if existing_result is None:\n        ensure_minimum_credit(user_id)',
    '    if existing_result is None:\n        preparation_started_at = time.perf_counter()\n        ensure_minimum_credit(user_id)',
    1,
)

worker = worker.replace(
    '        diagnosis_state = load_diagnosis_state(user_id, operation)\n        sources: list[dict] = []',
    '        diagnosis_state = load_diagnosis_state(user_id, operation)\n        timings["preparation_ms"] = _elapsed_ms(preparation_started_at)\n        sources: list[dict] = []',
    1,
)

worker = worker.replace(
    '        if should_research_web(original_message, operation):\n            research = research_web(original_message)',
    '        if should_research_web(original_message, operation):\n            research_started_at = time.perf_counter()\n            research = research_web(original_message)\n            timings["research_ms"] = _elapsed_ms(research_started_at)',
    1,
)

worker = worker.replace(
    '        result = generate_orchestrated_response(\n',
    '        intelligence_started_at = time.perf_counter()\n        result = generate_orchestrated_response(\n',
    1,
)

worker = worker.replace(
    '            diagnosis_state=diagnosis_state,\n        )\n        reply = result.text',
    '            diagnosis_state=diagnosis_state,\n        )\n        timings["intelligence_ms"] = _elapsed_ms(intelligence_started_at)\n        timings.update(getattr(result, "timings", None) or {})\n        reply = result.text',
    1,
)

worker = worker.replace(
    '        artifacts: list[dict] = []\n        decision = decide_artifact(',
    '        artifacts: list[dict] = []\n        artifact_started_at = time.perf_counter()\n        decision = decide_artifact(',
    1,
)

worker = worker.replace(
    '        existing_result = {\n            "reply": reply,',
    '        timings["artifact_ms"] = _elapsed_ms(artifact_started_at)\n        timings["generation_total_ms"] = _elapsed_ms(task_started_at)\n        existing_result = {\n            "reply": reply,',
    1,
)

worker = worker.replace(
    '            "sources": sources,\n        }',
    '            "sources": sources,\n            "timings": timings,\n        }',
    1,
)

worker = worker.replace(
    '    usage = charge_usage(user_id, meter_result, idempotency_key=f"chat-task:{task_id}")',
    '    billing_started_at = time.perf_counter()\n    usage = charge_usage(user_id, meter_result, idempotency_key=f"chat-task:{task_id}")\n    timings = dict(existing_result.get("timings") or timings)\n    timings["billing_ms"] = _elapsed_ms(billing_started_at)',
    1,
)

worker = worker.replace(
    '    existing_result["usage"] = usage\n    _append_completed_response(',
    '    existing_result["usage"] = usage\n    persistence_started_at = time.perf_counter()\n    _append_completed_response(',
    1,
)

worker = worker.replace(
    '    with session_scope() as db:\n        task = db.get(ChatTask, task_id)\n        if task is None:\n            return\n        task.result_json = json.dumps(existing_result, ensure_ascii=False)\n        task.status = "completed"',
    '    timings["persistence_ms"] = _elapsed_ms(persistence_started_at)\n    timings["total_ms"] = _elapsed_ms(task_started_at)\n    existing_result["timings"] = timings\n    with session_scope() as db:\n        task = db.get(ChatTask, task_id)\n        if task is None:\n            return\n        task.result_json = json.dumps(existing_result, ensure_ascii=False)\n        task.status = "completed"',
    1,
)

worker_path.write_text(worker, encoding='utf-8')

metered_path = Path('/app/app/services/metered_brain.py')
metered = metered_path.read_text(encoding='utf-8')

if 'import time\n' not in metered:
    metered = metered.replace('import os\n', 'import os\nimport time\n', 1)

metered = metered.replace(
    '    cached_input_tokens: int = 0\n    diagnosis_state: dict | None = None\n',
    '    cached_input_tokens: int = 0\n    diagnosis_state: dict | None = None\n    timings: dict | None = None\n',
    1,
)

metered = metered.replace(
    '    model = os.getenv("DOMNAI_OPENAI_MODEL", "gpt-4.1-mini").strip()\n    preflight_text, preflight_usage = (None, {})',
    '    model = os.getenv("DOMNAI_OPENAI_MODEL", "gpt-4.1-mini").strip()\n    stage_timings: dict[str, int] = {}\n    preflight_text, preflight_usage = (None, {})',
    1,
)

metered = metered.replace(
    '    if not attachments:\n        preflight_text, preflight_usage = _preflight_response(',
    '    if not attachments:\n        preflight_started_at = time.perf_counter()\n        preflight_text, preflight_usage = _preflight_response(',
    1,
)

metered = metered.replace(
    '            diagnosis_state,\n        )\n\n    if preflight_text:',
    '            diagnosis_state,\n        )\n        stage_timings["preflight_ms"] = max(0, round((time.perf_counter() - preflight_started_at) * 1000))\n\n    if preflight_text:',
    1,
)

metered = metered.replace(
    '    if preflight_text:\n        updated_state, memory_usage = _update_diagnosis_memory(',
    '    if preflight_text:\n        memory_started_at = time.perf_counter()\n        updated_state, memory_usage = _update_diagnosis_memory(',
    1,
)

metered = metered.replace(
    '            attachments,\n        )\n        input_tokens, output_tokens, cached_tokens = _usage_totals(preflight_usage, memory_usage)',
    '            attachments,\n        )\n        stage_timings["memory_ms"] = max(0, round((time.perf_counter() - memory_started_at) * 1000))\n        input_tokens, output_tokens, cached_tokens = _usage_totals(preflight_usage, memory_usage)',
    1,
)

metered = metered.replace(
    '            diagnosis_state=updated_state,\n        )\n\n    input_messages = _normalized_history(history)',
    '            diagnosis_state=updated_state,\n            timings=stage_timings,\n        )\n\n    input_messages = _normalized_history(history)',
    1,
)

metered = metered.replace(
    '    draft_text, draft_usage = _openai_request(\n',
    '    draft_started_at = time.perf_counter()\n    draft_text, draft_usage = _openai_request(\n',
    1,
)

metered = metered.replace(
    '        },\n    )\n\n    calculation_report, calculation_usage = _calculation_audit(api_key, model, message, draft_text, operation)',
    '        },\n    )\n    stage_timings["generation_ms"] = max(0, round((time.perf_counter() - draft_started_at) * 1000))\n\n    calculation_started_at = time.perf_counter()\n    calculation_report, calculation_usage = _calculation_audit(api_key, model, message, draft_text, operation)\n    stage_timings["calculation_ms"] = max(0, round((time.perf_counter() - calculation_started_at) * 1000))',
    1,
)

metered = metered.replace(
    '    if reviewed:\n        review_model = os.getenv("DOMNAI_REVIEW_MODEL", model).strip() or model',
    '    if reviewed:\n        review_started_at = time.perf_counter()\n        review_model = os.getenv("DOMNAI_REVIEW_MODEL", model).strip() or model',
    1,
)

metered = metered.replace(
    '            },\n        )\n\n    updated_state, memory_usage = _update_diagnosis_memory(',
    '            },\n        )\n        stage_timings["review_ms"] = max(0, round((time.perf_counter() - review_started_at) * 1000))\n    else:\n        stage_timings["review_ms"] = 0\n\n    memory_started_at = time.perf_counter()\n    updated_state, memory_usage = _update_diagnosis_memory(',
    1,
)

metered = metered.replace(
    '        attachments,\n    )\n\n    input_tokens, output_tokens, cached_tokens = _usage_totals(',
    '        attachments,\n    )\n    stage_timings["memory_ms"] = max(0, round((time.perf_counter() - memory_started_at) * 1000))\n\n    input_tokens, output_tokens, cached_tokens = _usage_totals(',
    1,
)

metered = metered.replace(
    '        diagnosis_state=updated_state,\n    )\n\n\ndef generate_metered_response(',
    '        diagnosis_state=updated_state,\n        timings=stage_timings,\n    )\n\n\ndef generate_metered_response(',
    1,
)

metered_path.write_text(metered, encoding='utf-8')

orchestrated_path = Path('/app/app/services/orchestrated_brain.py')
orchestrated = orchestrated_path.read_text(encoding='utf-8')

if 'import time\n' not in orchestrated:
    orchestrated = orchestrated.replace('import os\n', 'import os\nimport time\n', 1)

orchestrated = orchestrated.replace(
    '    try:\n        raw_plan, plan_usage = _openai_request(',
    '    orchestrator_started_at = time.perf_counter()\n    try:\n        raw_plan, plan_usage = _openai_request(',
    1,
)

orchestrated = orchestrated.replace(
    '        plan = {}\n        plan_usage = {}\n\n    engine = _specialized_engine(plan, operation, message)',
    '        plan = {}\n        plan_usage = {}\n\n    orchestrator_ms = max(0, round((time.perf_counter() - orchestrator_started_at) * 1000))\n    engine = _specialized_engine(plan, operation, message)',
    1,
)

orchestrated = orchestrated.replace(
    '        diagnosis_state=base_result.diagnosis_state,\n    )',
    '        diagnosis_state=base_result.diagnosis_state,\n        timings={"orchestrator_ms": orchestrator_ms, **(base_result.timings or {})},\n    )',
    1,
)

orchestrated_path.write_text(orchestrated, encoding='utf-8')

required_markers = (
    '"orchestrator_ms"',
    '"preflight_ms"',
    '"generation_ms"',
    '"calculation_ms"',
    '"review_ms"',
    '"memory_ms"',
    'timings.update(getattr(result, "timings", None) or {})',
)
combined = worker + metered + orchestrated
missing = [marker for marker in required_markers if marker not in combined]
if missing:
    raise RuntimeError(f'Instrumentação detalhada incompleta: {missing}')
