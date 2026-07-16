from pathlib import Path

# 1) Manter compatibilidade com o payload já publicado.
chat_path = Path('/app/app/api/chat.py')
chat = chat_path.read_text(encoding='utf-8')
chat_marker = '    attachments: list[ChatAttachmentItem] = Field(default_factory=list, max_length=10)\n'
if 'local_hour: int | None' not in chat:
    if chat_marker not in chat:
        raise RuntimeError('Modelo ChatRequest não encontrado para adicionar local_hour.')
    chat = chat.replace(
        chat_marker,
        chat_marker + '    local_hour: int | None = Field(default=None, ge=0, le=23)\n',
        1,
    )
chat_path.write_text(chat, encoding='utf-8')

# 2) Resolver o primeiro nome pelo perfil autenticado e persistir no payload da tarefa.
persistent_path = Path('/app/app/api/chat_persistent.py')
persistent = persistent_path.read_text(encoding='utf-8')
persistent = persistent.replace(
    'from app.models import ActiveChatState, ChatTask, LibraryAsset',
    'from app.models import ActiveChatState, ChatTask, LibraryAsset, UserProfile',
    1,
)

helper = '''\n\ndef _first_name_for_user(user_id: str) -> str:\n    with session_scope() as db:\n        profile = db.get(UserProfile, user_id)\n        full_name = str(profile.full_name or '').strip() if profile else ''\n    if not full_name:\n        return ''\n    return full_name.split()[0][:80]\n'''
if 'def _first_name_for_user(user_id: str)' not in persistent:
    marker = 'router = APIRouter(prefix="/api/chat", tags=["chat-persistent"])\n'
    if marker not in persistent:
        raise RuntimeError('Router persistente não encontrado para inserir resolução do primeiro nome.')
    persistent = persistent.replace(marker, marker + helper, 1)

if 'user_name = _first_name_for_user(user_id)' not in persistent:
    marker = '    now = datetime.now(timezone.utc)\n'
    if marker not in persistent:
        raise RuntimeError('Ponto de criação da tarefa persistente não encontrado.')
    persistent = persistent.replace(
        marker,
        '    user_name = _first_name_for_user(user_id)\n' + marker,
        1,
    )

payload_marker = '''                "attachment_ids": attachment_ids,\n                "local_artifact_followup": local_artifact_followup,'''
payload_replacement = '''                "attachment_ids": attachment_ids,\n                "local_artifact_followup": local_artifact_followup,\n                "user_name": user_name,\n                "local_hour": payload.local_hour,'''
if '"user_name": user_name' not in persistent:
    if payload_marker not in persistent:
        raise RuntimeError('Payload persistente não encontrado para adicionar personalização.')
    persistent = persistent.replace(payload_marker, payload_replacement, 1)

persistent_path.write_text(persistent, encoding='utf-8')

# 3) Usar o nome somente na primeira resposta estruturada de uma operação.
worker_path = Path('/app/app/services/chat_task_worker.py')
worker = worker_path.read_text(encoding='utf-8')

if 'user_name = str(payload.get("user_name") or "").strip()' not in worker:
    marker = '        history = payload.get("history") or []\n'
    if marker not in worker:
        raise RuntimeError('Histórico da tarefa não encontrado para personalização.')
    worker = worker.replace(
        marker,
        marker + '        user_name = str(payload.get("user_name") or "").strip()[:80]\n',
        1,
    )

old_message = '''        sources: list[dict] = []\n        message_for_brain = original_message\n'''
new_message = '''        sources: list[dict] = []\n        personal_context = ""\n        if user_name and operation and not history:\n            personal_context = (\n                f"CONTEXTO INTERNO DE PERSONALIZAÇÃO: o primeiro nome do usuário autenticado é {user_name}. "\n                "Esta é a abertura de uma operação estruturada. Inicie a resposta usando o primeiro nome de forma natural, "\n                "como 'Max, para começar...' ou equivalente adequado ao conteúdo. Não use bom dia, boa tarde, boa noite, "\n                "olá ou como vai automaticamente. Não explique este contexto.\\n\\n"\n            )\n        message_for_brain = f"{personal_context}{original_message}"\n'''
if 'CONTEXTO INTERNO DE PERSONALIZAÇÃO' not in worker:
    if old_message not in worker:
        raise RuntimeError('Preparação da mensagem do motor não encontrada para personalização.')
    worker = worker.replace(old_message, new_message, 1)

old_research = '''            message_for_brain = (\n                f"{original_message}\\n\\nPESQUISA WEB VERIFICADA:\\n{research.text}\\n\\n"\n                "Use os fatos pesquisados e não invente fontes ou URLs."\n            )'''
new_research = '''            message_for_brain = (\n                f"{personal_context}{original_message}\\n\\nPESQUISA WEB VERIFICADA:\\n{research.text}\\n\\n"\n                "Use os fatos pesquisados e não invente fontes ou URLs."\n            )'''
if old_research in worker:
    worker = worker.replace(old_research, new_research, 1)
elif new_research not in worker:
    raise RuntimeError('Bloco de pesquisa não encontrado para manter a personalização.')

worker_path.write_text(worker, encoding='utf-8')