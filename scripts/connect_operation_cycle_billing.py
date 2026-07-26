from pathlib import Path
import re


WORKER_PATH = Path('/app/app/services/chat_task_worker.py')


HELPER = '''def _resolve_operation_cycle_usage(user_id: str, payload: dict) -> dict:
    requested_text = str(payload.get("message") or "").strip()
    with session_scope() as db:
        state = db.get(ActiveChatState, user_id)
        try:
            messages = json.loads((state.messages_json if state is not None else "[]") or "[]")
            if not isinstance(messages, list):
                messages = []
        except json.JSONDecodeError:
            messages = []

    previous_context_state = latest_cycle_state(messages)
    continuity_observation = classify_continuity(
        operation=payload.get("operation"),
        previous_state=previous_context_state,
        new_message=requested_text,
        last_delivery=str((previous_context_state or {}).get("lastDeliverySummary") or ""),
    )
    provisional_state = build_cycle_state(
        operation=payload.get("operation"),
        message=requested_text,
        previous=previous_context_state,
        force_new=bool(payload.get("force_new_cycle")),
        continuity_observation=continuity_observation,
        last_delivery="",
    )
    cycle_id = str(provisional_state.get("cycleId") or "").strip()
    charge_decision = dict(provisional_state.get("chargeDecision") or {})
    decision = str(charge_decision.get("decision") or "").strip()

    usage = {
        "credits": 0,
        "charged_credits": 0,
        "operation_cycle_id": cycle_id,
        "charge_decision": charge_decision,
        "debitExecuted": False,
    }
    if decision == "COBRAR":
        charged = charge_operation_cycle(
            user_id,
            cycle_id,
            operation=payload.get("operation"),
            reason=charge_decision.get("reason"),
        )
        usage.update(charged)
        usage["credits"] = 7
        usage["operation_cycle_id"] = cycle_id
        usage["charge_decision"] = charge_decision
        usage["debitExecuted"] = True
    return usage
'''


RESOLVED_CONTEXT = '''        resolved_cycle_id = str(payload.get("resolved_cycle_id") or "").strip()
        if resolved_cycle_id:
            context_state["cycleId"] = resolved_cycle_id
        resolved_charge_decision = payload.get("resolved_charge_decision")
        if isinstance(resolved_charge_decision, dict):
            context_state["chargeDecision"] = {
                **resolved_charge_decision,
                "mode": "active",
                "debitExecuted": bool(payload.get("operation_cycle_debit_executed")),
            }
'''


PERSISTED_USAGE = '''    operation_usage = existing_result.get("usage") or {}
    payload["resolved_cycle_id"] = operation_usage.get("operation_cycle_id")
    payload["resolved_charge_decision"] = operation_usage.get("charge_decision")
    payload["operation_cycle_debit_executed"] = bool(operation_usage.get("debitExecuted"))

'''


def main() -> None:
    source = WORKER_PATH.read_text(encoding='utf-8')

    old_import = 'from app.services.credit_meter import charge_usage, ensure_minimum_credit\n'
    new_import = 'from app.services.credit_meter import charge_operation_cycle, ensure_minimum_credit\n'
    if old_import in source:
        source = source.replace(old_import, new_import, 1)
    elif new_import not in source:
        raise RuntimeError('Importação de cobrança do worker não localizada.')

    if 'def _resolve_operation_cycle_usage(' not in source:
        marker = 'def _process_task(task_id: str) -> None:\n'
        if marker not in source:
            raise RuntimeError('Entrada do processamento da tarefa não localizada.')
        source = source.replace(marker, HELPER.rstrip() + '\n\n\n' + marker, 1)

    old_billing = 'usage = charge_usage(user_id, result, idempotency_key=f"chat-task:{task_id}")'
    new_billing = 'usage = _resolve_operation_cycle_usage(user_id, payload)'
    if old_billing in source:
        source = source.replace(old_billing, new_billing, 1)

    fallback_pattern = re.compile(
        r'    if existing_result\.get\("usage"\) is None:.*?    else:\n        timings = dict\(existing_result\.get\("timings"\) or timings\)\n',
        flags=re.S,
    )
    fallback_replacement = '''    if existing_result.get("usage") is None:
        billing_started_at = time.perf_counter()
        existing_result["usage"] = _resolve_operation_cycle_usage(user_id, payload)
        timings = dict(existing_result.get("timings") or timings)
        timings["billing_ms"] = _elapsed_ms(billing_started_at)
    else:
        timings = dict(existing_result.get("timings") or timings)
'''
    source, fallback_count = fallback_pattern.subn(fallback_replacement, source, count=1)
    if fallback_count != 1:
        raise RuntimeError('Fallback de cobrança anterior não localizado uma única vez.')

    build_anchor = '            last_delivery=str(reply or ""),\n        )\n\n        user_index = None\n'
    if RESOLVED_CONTEXT.strip() not in source:
        if build_anchor not in source:
            raise RuntimeError('Construção do estado final não localizada.')
        source = source.replace(
            build_anchor,
            '            last_delivery=str(reply or ""),\n        )\n' + RESOLVED_CONTEXT + '\n        user_index = None\n',
            1,
        )

    persistence_anchor = '    persistence_started_at = time.perf_counter()\n'
    if PERSISTED_USAGE.strip() not in source:
        if persistence_anchor not in source:
            raise RuntimeError('Persistência final não localizada.')
        source = source.replace(persistence_anchor, PERSISTED_USAGE + persistence_anchor, 1)

    checks = {
        'helper por ciclo': source.count('def _resolve_operation_cycle_usage('),
        'cobrança fixa chamada': source.count('charge_operation_cycle('),
        'cobrança variável removida': source.count('charge_usage('),
        'resolução de ciclo persistida': source.count('payload["resolved_cycle_id"]'),
        'débito refletido no estado': source.count('"debitExecuted": bool(payload.get("operation_cycle_debit_executed"))'),
    }
    if checks['helper por ciclo'] != 1:
        raise RuntimeError(f'Helper de ciclo inválido: {checks}')
    if checks['cobrança fixa chamada'] != 1:
        raise RuntimeError(f'Chamada da cobrança fixa inválida: {checks}')
    if checks['cobrança variável removida'] != 0:
        raise RuntimeError(f'Cobrança variável ainda presente: {checks}')
    if checks['resolução de ciclo persistida'] != 1 or checks['débito refletido no estado'] != 1:
        raise RuntimeError(f'Persistência da cobrança por ciclo inválida: {checks}')

    compile(source, str(WORKER_PATH), 'exec')
    WORKER_PATH.write_text(source, encoding='utf-8')
    print('Cobrança variável removida e cobrança fixa por ciclo conectada com sucesso.')


if __name__ == '__main__':
    main()
