from pathlib import Path
import re
import sys


WORKER_PATH = Path('/app/app/services/chat_task_worker.py')
APP_ROOT = '/app'


CANONICAL_APPEND = '''def _append_completed_response(
    user_id: str,
    payload: dict,
    reply: str,
    artifacts: list[dict],
    sources: list[dict],
) -> None:
    task_id = str(payload.get("task_id") or "")
    if not task_id:
        return

    unique_artifacts: list[dict] = []
    seen_artifacts: set[str] = set()
    for artifact in artifacts or []:
        if not isinstance(artifact, dict):
            continue
        key = str(
            artifact.get("libraryId")
            or artifact.get("id")
            or artifact.get("contentUrl")
            or artifact.get("name")
            or ""
        )
        if not key or key in seen_artifacts:
            continue
        seen_artifacts.add(key)
        unique_artifacts.append(artifact)
        break

    requested_text = str(payload.get("message") or "").strip()

    with session_scope() as db:
        state = db.get(ActiveChatState, user_id)
        if state is None:
            state = ActiveChatState(user_id=user_id, messages_json="[]")
            db.add(state)
        try:
            messages = json.loads(state.messages_json or "[]")
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
        context_state = build_cycle_state(
            operation=payload.get("operation"),
            message=requested_text,
            previous=previous_context_state,
            force_new=bool(payload.get("force_new_cycle")),
            continuity_observation=continuity_observation,
            last_delivery=str(reply or ""),
        )

        user_index = None
        assistant_index = None
        normalized_messages = []

        for item in messages:
            if not isinstance(item, dict):
                normalized_messages.append(item)
                continue

            same_task = str(item.get("taskId") or "") == task_id
            role = item.get("role")

            if same_task and role == "user":
                if user_index is None:
                    user_index = len(normalized_messages)
                    normalized_messages.append(item)
                continue

            if same_task and role == "assistant":
                if assistant_index is None:
                    assistant_index = len(normalized_messages)
                    normalized_messages.append(item)
                continue

            normalized_messages.append(item)

        messages = normalized_messages

        if user_index is None and requested_text:
            for index in range(len(messages) - 1, -1, -1):
                item = messages[index]
                if not isinstance(item, dict) or item.get("role") != "user":
                    continue
                if str(item.get("taskId") or ""):
                    continue
                if str(item.get("text") or "").strip() != requested_text:
                    continue
                user_index = index
                break

        user_message = {
            "id": f"user-{task_id}",
            "role": "user",
            "text": requested_text,
            "attachments": [],
            "sources": [],
            "isError": False,
            "taskId": task_id,
            "processing": False,
        }
        if user_index is None:
            messages.append(user_message)
        else:
            messages[user_index] = {**messages[user_index], **user_message}

        final_message = {
            "id": f"assistant-{task_id}",
            "role": "assistant",
            "text": str(reply or "").strip(),
            "attachments": unique_artifacts,
            "sources": sources or [],
            "isError": False,
            "taskId": task_id,
            "processing": False,
            "contextState": context_state,
        }
        if assistant_index is None:
            messages.append(final_message)
        else:
            messages[assistant_index] = {**messages[assistant_index], **final_message}

        state.messages_json = json.dumps(messages[-300:], ensure_ascii=False)
        state.active_operation = payload.get("operation")
        state.updated_at = _now()
'''


def _test_cycle_logic() -> None:
    if APP_ROOT not in sys.path:
        sys.path.insert(0, APP_ROOT)

    from app.services.continuity_classifier import (
        AMBIGUOUS,
        CONTINUATION,
        CORRECTION,
        NEW_SUBJECT,
        classify_continuity,
    )
    from app.services.conversation_cycle import build_cycle_state, latest_cycle_state, objective_cycle_event

    first = build_cycle_state(operation="Análise imobiliária", message="Quero avaliar um imóvel.", previous=None)
    continued = build_cycle_state(operation="Análise imobiliária", message="O imóvel tem 120 m².", previous=first)
    changed = build_cycle_state(operation="Exercício em casa", message="Monte um treino.", previous=continued)
    restarted = build_cycle_state(
        operation="Exercício em casa",
        message="Quero começar outra análise.",
        previous=changed,
        force_new=True,
    )

    assert first["cycleReason"] == "first_conversation"
    assert first["opensNewCycle"] is True
    assert continued["cycleId"] == first["cycleId"]
    assert continued["cycleReason"] == "continuation"
    assert continued["opensNewCycle"] is False
    assert changed["cycleId"] != continued["cycleId"]
    assert changed["cycleReason"] == "operation_changed"
    assert restarted["cycleId"] != changed["cycleId"]
    assert restarted["cycleReason"] == "explicit_restart"
    assert objective_cycle_event(operation="Análise imobiliária", previous=first) == {
        "opensNewCycle": False,
        "reason": "continuation",
    }
    assert latest_cycle_state([{"role": "assistant", "contextState": continued}])["cycleId"] == continued["cycleId"]
    assert latest_cycle_state([{"role": "assistant"}]) is None

    base_state = build_cycle_state(
        operation="Análise imobiliária",
        message="Quero avaliar um imóvel e as opções de financiamento.",
        previous=None,
        last_delivery="Análise do imóvel e das condições de financiamento.",
    )
    correction = classify_continuity(
        operation="Análise imobiliária",
        previous_state=base_state,
        new_message="Na verdade, o imóvel tem 120 m², não 100.",
    )
    continuation = classify_continuity(
        operation="Análise imobiliária",
        previous_state=base_state,
        new_message="E se eu financiar em 20 anos?",
    )
    new_subject = classify_continuity(
        operation="Análise imobiliária",
        previous_state=base_state,
        new_message="Agora monte um treino para fazer em casa.",
    )
    ambiguous = classify_continuity(
        operation="Análise imobiliária",
        previous_state=base_state,
        new_message="Também quero uma orientação diferente.",
    )

    assert correction["label"] == CORRECTION
    assert continuation["label"] == CONTINUATION
    assert new_subject["label"] == NEW_SUBJECT
    assert new_subject["confidence"] >= 0.90
    assert ambiguous["label"] == AMBIGUOUS
    assert ambiguous["requiresConfirmation"] is True


def _test_operation_cycle_billing_contract() -> None:
    if APP_ROOT not in sys.path:
        sys.path.insert(0, APP_ROOT)

    from app.services.credit_meter import (
        OPERATION_CYCLE_CREDITS,
        charge_operation_cycle,
        operation_cycle_idempotency_key,
    )

    assert OPERATION_CYCLE_CREDITS == 7
    first_key = operation_cycle_idempotency_key("user-123", "cycle-abc")
    repeated_key = operation_cycle_idempotency_key("user-123", "cycle-abc")
    other_cycle_key = operation_cycle_idempotency_key("user-123", "cycle-def")
    assert first_key == "operation-cycle:user-123:cycle-abc"
    assert repeated_key == first_key
    assert other_cycle_key != first_key

    credit_source = Path('/app/app/services/credit_meter.py').read_text(encoding='utf-8')
    assert credit_source.count('def charge_operation_cycle(') == 1
    assert '.with_for_update()' in credit_source
    assert 'CreditTransaction.stripe_event_id == idempotency_key' in credit_source
    assert 'kind="operation_cycle"' in credit_source
    assert 'amount=-OPERATION_CYCLE_CREDITS' in credit_source
    assert callable(charge_operation_cycle)


def main() -> None:
    source = WORKER_PATH.read_text(encoding='utf-8')

    cycle_import = 'from app.services.conversation_cycle import build_cycle_state, latest_cycle_state\n'
    classifier_import = 'from app.services.continuity_classifier import classify_continuity\n'
    if cycle_import not in source:
        source, import_count = re.subn(
            r'(from app\.services\.credit_meter import [^\n]+\n)',
            r'\1' + cycle_import,
            source,
            count=1,
        )
        if import_count != 1:
            raise RuntimeError('Importação de credit_meter não localizada no worker transformado.')
    if classifier_import not in source:
        if cycle_import not in source:
            raise RuntimeError('Importação do ciclo não localizada para ancorar o classificador.')
        source = source.replace(cycle_import, cycle_import + classifier_import, 1)

    pattern = re.compile(r'def _append_completed_response\(.*?\n(?=def _process_task\()', flags=re.S)
    source, count = pattern.subn(CANONICAL_APPEND.rstrip() + '\n\n', source, count=1)
    if count != 1:
        raise RuntimeError('Função de persistência final do chat não localizada.')

    checks = {
        'função de persistência': source.count('def _append_completed_response('),
        'estado persistido': source.count('"contextState": context_state'),
        'construção do ciclo': source.count('build_cycle_state('),
        'leitura do ciclo': source.count('latest_cycle_state('),
        'importação do ciclo': source.count(cycle_import.strip()),
        'importação do classificador': source.count(classifier_import.strip()),
        'classificação observada': source.count('continuity_observation = classify_continuity('),
        'sinal objetivo de reinício': source.count('force_new=bool(payload.get("force_new_cycle"))'),
    }
    invalid = {name: count for name, count in checks.items() if count != 1}
    if invalid:
        raise RuntimeError(f'Validação estrutural do ciclo falhou: {invalid}')

    compile(source, str(WORKER_PATH), 'exec')
    WORKER_PATH.write_text(source, encoding='utf-8')
    _test_cycle_logic()
    _test_operation_cycle_billing_contract()
    print('Ciclo, classificador e contrato de débito idempotente testados com sucesso.')


if __name__ == '__main__':
    main()
