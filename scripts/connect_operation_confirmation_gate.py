from pathlib import Path
import re


WORKER_PATH = Path('/app/app/services/chat_task_worker.py')


HELPERS = '''_CONFIRM_POSITIVE = {"sim", "sim quero", "confirmo", "pode continuar", "pode iniciar", "iniciar nova operacao", "nova operacao"}
_CONFIRM_NEGATIVE = {"nao", "não", "cancelar", "cancela", "deixa", "continuar assunto atual", "manter assunto atual"}
_CONFIRMATION_TEXT = "Esse pedido parece iniciar uma análise diferente. Deseja continuar como uma nova operação?"


def _normalized_confirmation(value: str) -> str:
    return " ".join(str(value or "").strip().casefold().split())


def _confirmation_intent(value: str) -> str:
    normalized = _normalized_confirmation(value)
    if normalized in _CONFIRM_POSITIVE:
        return "confirm"
    if normalized in _CONFIRM_NEGATIVE:
        return "reject"
    return "unknown"


def _latest_pending_analysis(user_id: str) -> dict | None:
    with session_scope() as db:
        state = db.get(ActiveChatState, user_id)
        try:
            messages = json.loads((state.messages_json if state is not None else "[]") or "[]")
            if not isinstance(messages, list):
                messages = []
        except json.JSONDecodeError:
            messages = []
    context_state = latest_cycle_state(messages)
    pending = (context_state or {}).get("pendingNewAnalysis")
    return dict(pending) if isinstance(pending, dict) and str(pending.get("message") or "").strip() else None


def _classify_operation_gate(user_id: str, payload: dict) -> dict:
    requested_text = str(payload.get("message") or "").strip()
    pending = _latest_pending_analysis(user_id)
    if pending is not None:
        intent = _confirmation_intent(requested_text)
        if intent == "confirm":
            return {"action": "confirm", "pending": pending}
        if intent == "reject":
            return {"action": "reject", "pending": pending}
        return {"action": "ask_again", "pending": pending}

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
    charge_decision = dict(provisional_state.get("chargeDecision") or {})
    if str(charge_decision.get("decision") or "") == "PEDIR_CONFIRMACAO":
        return {
            "action": "ask",
            "pending": {
                "message": requested_text,
                "operation": payload.get("operation"),
                "requestedAtTaskId": payload.get("task_id"),
            },
            "cycle_id": provisional_state.get("cycleId"),
            "charge_decision": charge_decision,
        }
    return {"action": "continue"}


def _complete_confirmation_gate_task(
    *,
    task_id: str,
    user_id: str,
    payload: dict,
    reply: str,
    pending: dict | None,
    clear_pending: bool,
    cycle_id: str | None = None,
    charge_decision: dict | None = None,
) -> None:
    usage = {
        "credits": 0,
        "charged_credits": 0,
        "operation_cycle_id": cycle_id,
        "charge_decision": charge_decision or {
            "decision": "PEDIR_CONFIRMACAO",
            "reason": "confirmation_gate",
            "confidence": 0.0,
            "source": "safety_gate",
        },
        "debitExecuted": False,
        "confirmationGate": True,
    }
    payload["resolved_cycle_id"] = cycle_id
    payload["resolved_charge_decision"] = usage["charge_decision"]
    payload["operation_cycle_debit_executed"] = False
    payload["pending_new_analysis"] = pending
    payload["clear_pending_new_analysis"] = clear_pending
    _append_completed_response(user_id, payload, reply, [], [])
    completed = {
        "reply": reply,
        "artifacts": [],
        "provider": "local-confirmation-gate",
        "model": "deterministic",
        "input_tokens": 0,
        "output_tokens": 0,
        "cached_input_tokens": 0,
        "diagnosis_state": None,
        "sources": [],
        "timings": {"confirmation_gate_ms": 0},
        "usage": usage,
    }
    with session_scope() as db:
        task = db.get(ChatTask, task_id)
        if task is None:
            return
        task.result_json = json.dumps(completed, ensure_ascii=False)
        task.status = "completed"
        task.completed_at = _now()
        task.updated_at = _now()
        task.credit_transaction_key = None
'''


ENTRY_GATE = '''    if existing_result is None:
        operation_gate = _classify_operation_gate(user_id, payload)
        gate_action = str(operation_gate.get("action") or "continue")
        if gate_action == "confirm":
            pending = dict(operation_gate.get("pending") or {})
            payload["message"] = str(pending.get("message") or payload.get("message") or "").strip()
            payload["operation"] = pending.get("operation") or payload.get("operation")
            operation = payload.get("operation")
            payload["force_new_cycle"] = True
            payload["clear_pending_new_analysis"] = True
        elif gate_action == "reject":
            _complete_confirmation_gate_task(
                task_id=task_id,
                user_id=user_id,
                payload=payload,
                reply="Certo. O assunto atual foi mantido e nenhuma nova operação foi iniciada.",
                pending=None,
                clear_pending=True,
            )
            return
        elif gate_action in {"ask", "ask_again"}:
            pending = dict(operation_gate.get("pending") or {})
            _complete_confirmation_gate_task(
                task_id=task_id,
                user_id=user_id,
                payload=payload,
                reply=_CONFIRMATION_TEXT,
                pending=pending,
                clear_pending=False,
                cycle_id=operation_gate.get("cycle_id"),
                charge_decision=operation_gate.get("charge_decision"),
            )
            return

'''


PENDING_CONTEXT = '''        pending_new_analysis = payload.get("pending_new_analysis")
        if isinstance(pending_new_analysis, dict) and str(pending_new_analysis.get("message") or "").strip():
            context_state["pendingNewAnalysis"] = {
                "message": str(pending_new_analysis.get("message") or "").strip()[:2000],
                "operation": pending_new_analysis.get("operation"),
                "requestedAtTaskId": pending_new_analysis.get("requestedAtTaskId"),
            }
        elif bool(payload.get("clear_pending_new_analysis")):
            context_state.pop("pendingNewAnalysis", None)
'''


def main() -> None:
    source = WORKER_PATH.read_text(encoding='utf-8')

    if 'def _classify_operation_gate(' not in source:
        marker = 'def _resolve_operation_cycle_usage(user_id: str, payload: dict) -> dict:\n'
        if marker not in source:
            raise RuntimeError('Helper de cobrança por ciclo não localizado para inserir o gate.')
        source = source.replace(marker, HELPERS.rstrip() + '\n\n\n' + marker, 1)

    entry_anchor = '    if existing_result is None:\n        preparation_started_at = time.perf_counter()\n'
    if ENTRY_GATE.strip() not in source:
        if entry_anchor not in source:
            raise RuntimeError('Entrada do processamento normal não localizada.')
        source = source.replace(
            entry_anchor,
            ENTRY_GATE + '    if existing_result is None:\n        preparation_started_at = time.perf_counter()\n',
            1,
        )

    context_anchor = '        resolved_charge_decision = payload.get("resolved_charge_decision")\n'
    if PENDING_CONTEXT.strip() not in source:
        if context_anchor not in source:
            raise RuntimeError('Persistência da decisão resolvida não localizada.')
        source = source.replace(context_anchor, PENDING_CONTEXT + '\n' + context_anchor, 1)

    checks = {
        'gate classificador': source.count('def _classify_operation_gate('),
        'finalização sem IA': source.count('def _complete_confirmation_gate_task('),
        'entrada do gate': source.count('operation_gate = _classify_operation_gate(user_id, payload)'),
        'pergunta oficial': source.count('_CONFIRMATION_TEXT ='),
        'persistência pendente': source.count('context_state["pendingNewAnalysis"] ='),
        'limpeza pendente': source.count('context_state.pop("pendingNewAnalysis", None)'),
        'confirmação força ciclo': source.count('payload["force_new_cycle"] = True'),
    }
    invalid = {name: count for name, count in checks.items() if count != 1}
    if invalid:
        raise RuntimeError(f'Gate de confirmação estruturalmente inválido: {invalid}')

    compile(source, str(WORKER_PATH), 'exec')

    namespace = {}
    exec(compile('_CONFIRM_POSITIVE = {"sim", "confirmo"}\n_CONFIRM_NEGATIVE = {"nao", "não"}\n' +
                 'def _normalized_confirmation(value): return " ".join(str(value or "").strip().casefold().split())\n' +
                 'def _confirmation_intent(value):\n' +
                 '    normalized = _normalized_confirmation(value)\n' +
                 '    if normalized in _CONFIRM_POSITIVE: return "confirm"\n' +
                 '    if normalized in _CONFIRM_NEGATIVE: return "reject"\n' +
                 '    return "unknown"\n', '<confirmation-contract>', 'exec'), namespace)
    assert namespace['_confirmation_intent']('sim') == 'confirm'
    assert namespace['_confirmation_intent']('não') == 'reject'
    assert namespace['_confirmation_intent']('talvez') == 'unknown'

    WORKER_PATH.write_text(source, encoding='utf-8')
    print('Gate de confirmação bloqueia geração e cobrança até decisão do usuário.')


if __name__ == '__main__':
    main()
