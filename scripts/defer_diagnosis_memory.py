from pathlib import Path

metered_path = Path('/app/app/services/metered_brain.py')
metered = metered_path.read_text(encoding='utf-8')

metered = metered.replace(
    '    cached_input_tokens: int = 0\n    diagnosis_state: dict | None = None\n',
    '    cached_input_tokens: int = 0\n    diagnosis_state: dict | None = None\n    deferred_memory: dict | None = None\n',
    1,
)

memory_wrapper = '''\n\ndef run_deferred_diagnosis_memory(job: dict) -> tuple[dict, dict]:\n    attachment_names = [str(name or "arquivo") for name in (job.get("attachment_names") or [])]\n    attachments = [{"name": name} for name in attachment_names]\n    return _update_diagnosis_memory(\n        str(job.get("api_key") or ""),\n        str(job.get("model") or "gpt-4.1-mini"),\n        job.get("operation"),\n        job.get("prior_state"),\n        str(job.get("message") or ""),\n        str(job.get("final_text") or ""),\n        attachments,\n    )\n'''
marker = '\n\ndef _openai_response(\n'
if 'def run_deferred_diagnosis_memory(job: dict)' not in metered:
    if marker not in metered:
        raise RuntimeError('Ponto da memória adiada não encontrado.')
    metered = metered.replace(marker, memory_wrapper + marker, 1)

old_preflight = '''    if preflight_text:\n        updated_state, memory_usage = _update_diagnosis_memory(\n            api_key,\n            model,\n            operation,\n            diagnosis_state,\n            message,\n            preflight_text,\n            attachments,\n        )\n        input_tokens, output_tokens, cached_tokens = _usage_totals(preflight_usage, memory_usage)\n        return MeteredBrainResult(\n            text=preflight_text,\n            provider="openai-preflight-memory",\n            model=model,\n            input_tokens=input_tokens,\n            output_tokens=output_tokens,\n            cached_input_tokens=cached_tokens,\n            diagnosis_state=updated_state,\n        )'''
new_preflight = '''    if preflight_text:\n        input_tokens, output_tokens, cached_tokens = _usage_totals(preflight_usage)\n        fallback_state = sanitize_diagnosis_state(diagnosis_state or {}, operation)\n        return MeteredBrainResult(\n            text=preflight_text,\n            provider="openai-preflight-deferred-memory",\n            model=model,\n            input_tokens=input_tokens,\n            output_tokens=output_tokens,\n            cached_input_tokens=cached_tokens,\n            diagnosis_state=fallback_state,\n            deferred_memory={\n                "api_key": api_key,\n                "model": model,\n                "operation": operation,\n                "prior_state": diagnosis_state,\n                "message": message,\n                "final_text": preflight_text,\n                "attachment_names": [str(item.get("name") or "arquivo") for item in attachments],\n            },\n        )'''
if old_preflight not in metered:
    raise RuntimeError('Bloco preflight com memória não encontrado.')
metered = metered.replace(old_preflight, new_preflight, 1)

old_final = '''    updated_state, memory_usage = _update_diagnosis_memory(\n        api_key,\n        model,\n        operation,\n        diagnosis_state,\n        message,\n        final_text,\n        attachments,\n    )\n\n    input_tokens, output_tokens, cached_tokens = _usage_totals(\n        preflight_usage,\n        draft_usage,\n        calculation_usage,\n        review_usage,\n        memory_usage,\n    )\n    return MeteredBrainResult(\n        text=final_text,\n        provider="openai-reviewed-calculated-memory" if calculation_report else "openai-reviewed-memory" if reviewed else "openai-memory",\n        model=model,\n        input_tokens=input_tokens,\n        output_tokens=output_tokens,\n        cached_input_tokens=cached_tokens,\n        diagnosis_state=updated_state,\n    )'''
new_final = '''    input_tokens, output_tokens, cached_tokens = _usage_totals(\n        preflight_usage,\n        draft_usage,\n        calculation_usage,\n        review_usage,\n    )\n    fallback_state = sanitize_diagnosis_state(diagnosis_state or {}, operation)\n    return MeteredBrainResult(\n        text=final_text,\n        provider="openai-reviewed-calculated-deferred-memory" if calculation_report else "openai-reviewed-deferred-memory" if reviewed else "openai-deferred-memory",\n        model=model,\n        input_tokens=input_tokens,\n        output_tokens=output_tokens,\n        cached_input_tokens=cached_tokens,\n        diagnosis_state=fallback_state,\n        deferred_memory={\n            "api_key": api_key,\n            "model": model,\n            "operation": operation,\n            "prior_state": diagnosis_state,\n            "message": message,\n            "final_text": final_text,\n            "attachment_names": [str(item.get("name") or "arquivo") for item in attachments],\n        },\n    )'''
if old_final not in metered:
    raise RuntimeError('Bloco final com memória não encontrado.')
metered = metered.replace(old_final, new_final, 1)
metered_path.write_text(metered, encoding='utf-8')

worker_path = Path('/app/app/services/chat_task_worker.py')
worker = worker_path.read_text(encoding='utf-8')
worker = worker.replace(
    '        timings["intelligence_ms"] = _elapsed_ms(intelligence_started_at)\n        reply = result.text',
    '        timings["intelligence_ms"] = _elapsed_ms(intelligence_started_at)\n        deferred_memory = getattr(result, "deferred_memory", None)\n        reply = result.text',
    1,
)
worker = worker.replace(
    '            "diagnosis_state": result.diagnosis_state,\n            "sources": sources,',
    '            "diagnosis_state": result.diagnosis_state,\n            "deferred_memory": deferred_memory,\n            "sources": sources,',
    1,
)

completion_marker = '''        task.credit_transaction_key = f"chat-task:{task_id}"\n'''
completion_replacement = '''        task.credit_transaction_key = f"chat-task:{task_id}"\n\n    deferred_memory = existing_result.get("deferred_memory")\n    if deferred_memory:\n        memory_started_at = time.perf_counter()\n        try:\n            from app.services.metered_brain import run_deferred_diagnosis_memory\n            updated_state, memory_usage = run_deferred_diagnosis_memory(deferred_memory)\n            save_diagnosis_state(user_id, payload.get("operation"), updated_state)\n            timings["memory_ms"] = _elapsed_ms(memory_started_at)\n            existing_result["diagnosis_state"] = updated_state\n            existing_result["memory_usage"] = memory_usage\n            existing_result["timings"] = timings\n            existing_result.pop("deferred_memory", None)\n            with session_scope() as db:\n                task = db.get(ChatTask, task_id)\n                if task is not None:\n                    task.result_json = json.dumps(existing_result, ensure_ascii=False)\n                    task.updated_at = _now()\n        except Exception as exc:\n            timings["memory_ms"] = _elapsed_ms(memory_started_at)\n            existing_result["memory_error"] = str(exc)[:500]\n            existing_result["timings"] = timings\n'''
if completion_marker not in worker:
    raise RuntimeError('Ponto pós-entrega não encontrado no worker.')
worker = worker.replace(completion_marker, completion_replacement, 1)
worker_path.write_text(worker, encoding='utf-8')
