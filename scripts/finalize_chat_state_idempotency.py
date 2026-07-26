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
        context_state = build_cycle_state(
            operation=payload.get("operation"),
            message=requested_text,
            previous=previous_context_state,
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

    from app.services.conversation_cycle import build_cycle_state, latest_cycle_state

    first = build_cycle_state(operation="Análise imobiliária", message="Quero avaliar um imóvel.", previous=None)
    continued = build_cycle_state(operation="Análise imobiliária", message="O imóvel tem 120 m².", previous=first)
    changed = build_cycle_state(operation="Exercício em casa", message="Monte um treino.", previous=continued)

    assert first["cycleId"] == continued["cycleId"]
    assert first["firstMessage"] == continued["firstMessage"]
    assert changed["cycleId"] != continued["cycleId"]
    assert latest_cycle_state([{"role": "assistant", "contextState": continued}])["cycleId"] == continued["cycleId"]
    assert latest_cycle_state([{"role": "assistant"}]) is None


def main() -> None:
    source = WORKER_PATH.read_text(encoding='utf-8')

    cycle_import = 'from app.services.conversation_cycle import build_cycle_state, latest_cycle_state\n'
    if cycle_import not in source:
        source, import_count = re.subn(
            r'(from app\.services\.credit_meter import [^\n]+\n)',
            r'\1' + cycle_import,
            source,
            count=1,
        )
        if import_count != 1:
            raise RuntimeError('Importação de credit_meter não localizada no worker transformado.')

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
    }
    invalid = {name: count for name, count in checks.items() if count != 1}
    if invalid:
        raise RuntimeError(f'Validação estrutural do ciclo falhou: {invalid}')

    compile(source, str(WORKER_PATH), 'exec')
    WORKER_PATH.write_text(source, encoding='utf-8')
    _test_cycle_logic()
    print('Persistência do chat e estado estruturado do ciclo testados com sucesso.')


if __name__ == '__main__':
    main()
