from pathlib import Path

MAX_CHAT_MESSAGES = 2000

chat_state_path = Path('/app/app/api/chat_state.py')
chat_state = chat_state_path.read_text(encoding='utf-8')

chat_state = chat_state.replace(
    'from sqlalchemy import select\n',
    'from sqlalchemy import select, update\n',
    1,
)
chat_state = chat_state.replace(
    'messages: list[dict] = Field(default_factory=list, max_length=300)',
    f'messages: list[dict] = Field(default_factory=list, max_length={MAX_CHAT_MESSAGES})',
)
chat_state = chat_state.replace(
    'for item in items[-300:]:',
    f'for item in items[-{MAX_CHAT_MESSAGES}:]:',
)
chat_state = chat_state.replace(
    'return merged[-300:]',
    f'return merged[-{MAX_CHAT_MESSAGES}:]',
)

clear_start = chat_state.index('@router.delete("")')
clear_anchor = '''    user_id = _user_id(session)
    with session_scope() as db:
        state = db.get(ActiveChatState, user_id)
'''
clear_replacement = '''    user_id = _user_id(session)
    with session_scope() as db:
        # Uma conversa apagada ganha uma fronteira real: tarefas antigas não podem
        # concluir depois e repovoar o novo chat com resposta fora de contexto.
        db.execute(
            update(ChatTask)
            .where(
                ChatTask.user_id == user_id,
                ChatTask.status.in_(("queued", "processing")),
            )
            .values(status="cancelled")
        )
        state = db.get(ActiveChatState, user_id)
'''
clear_anchor_index = chat_state.find(clear_anchor, clear_start)
if clear_anchor_index >= 0:
    chat_state = (
        chat_state[:clear_anchor_index]
        + clear_replacement
        + chat_state[clear_anchor_index + len(clear_anchor):]
    )
elif 'ChatTask.status.in_(("queued", "processing"))' not in chat_state:
    raise RuntimeError('Fronteira de cancelamento do novo chat não encontrada.')

if 'max_length=300' in chat_state or 'items[-300:]' in chat_state or 'merged[-300:]' in chat_state:
    raise RuntimeError('Nem todos os limites destrutivos de 300 mensagens foram removidos de chat_state.py.')
if 'values(status="cancelled")' not in chat_state:
    raise RuntimeError('Tarefas antigas não são canceladas ao limpar a conversa.')

chat_state_path.write_text(chat_state, encoding='utf-8')

worker_path = Path('/app/app/services/chat_task_worker.py')
worker = worker_path.read_text(encoding='utf-8')
worker = worker.replace(
    'state.messages_json = json.dumps(messages[-300:], ensure_ascii=False)',
    f'state.messages_json = json.dumps(messages[-{MAX_CHAT_MESSAGES}:], ensure_ascii=False)',
)

pre_billing_anchor = '''        billing_started_at = time.perf_counter()
        usage = charge_usage(user_id, result, idempotency_key=f"chat-task:{task_id}")
'''
pre_billing_guard = '''        with session_scope() as db:
            current_task = db.get(ChatTask, task_id)
            if current_task is None or current_task.status == "cancelled":
                return

        billing_started_at = time.perf_counter()
        usage = charge_usage(user_id, result, idempotency_key=f"chat-task:{task_id}")
'''
if pre_billing_guard not in worker:
    if pre_billing_anchor not in worker:
        raise RuntimeError('Ponto anterior à cobrança não encontrado para bloquear tarefa cancelada.')
    worker = worker.replace(pre_billing_anchor, pre_billing_guard, 1)

pre_persistence_anchor = '''    if existing_result.get("diagnosis_state") is not None:
'''
pre_persistence_guard = '''    with session_scope() as db:
        current_task = db.get(ChatTask, task_id)
        if current_task is None or current_task.status == "cancelled":
            return

    if existing_result.get("diagnosis_state") is not None:
'''
if pre_persistence_guard not in worker:
    if pre_persistence_anchor not in worker:
        raise RuntimeError('Ponto anterior à persistência não encontrado para bloquear tarefa cancelada.')
    worker = worker.replace(pre_persistence_anchor, pre_persistence_guard, 1)

if 'messages[-300:]' in worker:
    raise RuntimeError('O limite destrutivo de 300 mensagens ainda existe em chat_task_worker.py.')
if worker.count('current_task.status == "cancelled"') < 2:
    raise RuntimeError('Guardas de cancelamento não foram instaladas antes da cobrança e persistência.')

worker_path.write_text(worker, encoding='utf-8')
print('Histórico ampliado e fronteira de novo chat protegida contra tarefas antigas.')
