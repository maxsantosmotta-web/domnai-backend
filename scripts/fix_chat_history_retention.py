from pathlib import Path

MAX_CHAT_MESSAGES = 2000

chat_state_path = Path('/app/app/api/chat_state.py')
chat_state = chat_state_path.read_text(encoding='utf-8')

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

if 'max_length=300' in chat_state or 'items[-300:]' in chat_state or 'merged[-300:]' in chat_state:
    raise RuntimeError('Nem todos os limites destrutivos de 300 mensagens foram removidos de chat_state.py.')

chat_state_path.write_text(chat_state, encoding='utf-8')

worker_path = Path('/app/app/services/chat_task_worker.py')
worker = worker_path.read_text(encoding='utf-8')
worker = worker.replace(
    'state.messages_json = json.dumps(messages[-300:], ensure_ascii=False)',
    f'state.messages_json = json.dumps(messages[-{MAX_CHAT_MESSAGES}:], ensure_ascii=False)',
)

if 'messages[-300:]' in worker:
    raise RuntimeError('O limite destrutivo de 300 mensagens ainda existe em chat_task_worker.py.')

worker_path.write_text(worker, encoding='utf-8')
