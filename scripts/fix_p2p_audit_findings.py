from pathlib import Path

FRONTEND = Path('/frontend/src')
BACKEND = Path('/app/app')


def replace_once(source: str, old: str, new: str, label: str) -> str:
    if new in source:
        return source
    count = source.count(old)
    if count != 1:
        raise RuntimeError(f'{label}: estado final ausente e trecho antigo encontrado {count} vez(es).')
    return source.replace(old, new, 1)


def fix_frontend_profile() -> None:
    path = FRONTEND / 'dashboard-profile-enhancements.js'
    source = path.read_text(encoding='utf-8')

    helper = '''function profileEscapeHtml(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

'''
    if 'function profileEscapeHtml(value)' not in source:
        marker = 'function profileDigits(value) {'
        if source.count(marker) != 1:
            raise RuntimeError('Perfil principal: ponto seguro para auxiliar de escape não encontrado.')
        source = source.replace(marker, helper + marker, 1)

    replacements = {
        '${avatarUrl}': '${profileEscapeHtml(avatarUrl)}',
        '${initial}': '${profileEscapeHtml(initial)}',
        "${profile.fullName || 'Perfil incompleto'}": "${profileEscapeHtml(profile.fullName || 'Perfil incompleto')}",
        "${email || 'E-mail da conta'}": "${profileEscapeHtml(email || 'E-mail da conta')}",
        "${profile.fullName || ''}": "${profileEscapeHtml(profile.fullName || '')}",
        "${profileFormatPhone(profile.phone || '')}": "${profileEscapeHtml(profileFormatPhone(profile.phone || ''))}",
        "${profileFormatCpf(profile.cpf || '')}": "${profileEscapeHtml(profileFormatCpf(profile.cpf || ''))}",
        '${birth.day}': '${profileEscapeHtml(birth.day)}',
        '${birth.month}': '${profileEscapeHtml(birth.month)}',
        '${birth.year}': '${profileEscapeHtml(birth.year)}',
        "${profileFormatCep(profile.zipCode || '')}": "${profileEscapeHtml(profileFormatCep(profile.zipCode || ''))}",
        "${profile.street || ''}": "${profileEscapeHtml(profile.street || '')}",
        "${profile.number || ''}": "${profileEscapeHtml(profile.number || '')}",
        "${profile.complement || ''}": "${profileEscapeHtml(profile.complement || '')}",
        "${profile.lot || ''}": "${profileEscapeHtml(profile.lot || '')}",
        "${profile.block || ''}": "${profileEscapeHtml(profile.block || '')}",
        "${profile.building || ''}": "${profileEscapeHtml(profile.building || '')}",
        "${profile.apartment || ''}": "${profileEscapeHtml(profile.apartment || '')}",
        "${profile.neighborhood || ''}": "${profileEscapeHtml(profile.neighborhood || '')}",
        "${profile.city || ''}": "${profileEscapeHtml(profile.city || '')}",
        "${profile.state || ''}": "${profileEscapeHtml(profile.state || '')}",
    }

    for old, new in replacements.items():
        if new in source:
            continue
        count = source.count(old)
        if count < 1:
            raise RuntimeError(f'Perfil principal: valor dinâmico não encontrado para proteção: {old}')
        source = source.replace(old, new)

    path.write_text(source, encoding='utf-8')


def fix_backend_chat() -> None:
    worker_path = BACKEND / 'services' / 'chat_task_worker.py'
    worker = worker_path.read_text(encoding='utf-8')

    worker = replace_once(
        worker,
        'from app.database import session_scope\n',
        'from app.audit import record_audit_event\nfrom app.database import session_scope\n',
        'importação do registro de conclusão da conversa',
    )

    worker = replace_once(
        worker,
        '''            except Exception:\n                reply = "Não foi possível gerar o arquivo nesta tentativa."''',
        '''            except Exception:\n                reply = (\n                    f"{reply.rstrip()}\\n\\n"\n                    "A análise foi concluída, mas não foi possível gerar o arquivo nesta tentativa."\n                )''',
        'preservação da resposta quando o arquivo falha',
    )

    completion_old = '''        task.credit_transaction_key = f"chat-task:{task_id}"'''
    completion_new = '''        task.credit_transaction_key = f"chat-task:{task_id}"
        operation = str(payload.get("operation") or "").strip()
        record_audit_event(
            db,
            user_id=user_id,
            category="chat",
            module="Chat",
            action="conversation_completed",
            description=(
                f"Operação concluída: {operation}."
                if operation
                else "Conversa concluída com resposta entregue ao usuário."
            ),
            source="chat_task_worker",
            source_key=f"conversation:{task_id}",
        )'''
    worker = replace_once(
        worker,
        completion_old,
        completion_new,
        'registro idempotente da conclusão real da conversa',
    )
    worker_path.write_text(worker, encoding='utf-8')

    state_path = BACKEND / 'api' / 'chat_state.py'
    state = state_path.read_text(encoding='utf-8')
    delete_audit_block = '''            messages = _load_messages(state)
            if _has_completed_response(messages):
                operation = str(state.active_operation or "").strip()
                record_audit_event(
                    db,
                    user_id=user_id,
                    category="chat",
                    module="Chat",
                    action="conversation_completed",
                    description=(
                        f"Operação concluída: {operation}."
                        if operation
                        else "Conversa concluída pelo usuário."
                    ),
                    source="chat_state",
                    source_key=f"conversation:{user_id}:{state.updated_at.isoformat()}",
                )
'''
    if delete_audit_block in state:
        state = state.replace(delete_audit_block, '', 1)
    elif 'source="chat_state"' in state:
        raise RuntimeError('Remoção da contagem por exclusão: estrutura inesperada encontrada.')
    state_path.write_text(state, encoding='utf-8')


applied = []
if FRONTEND.exists():
    fix_frontend_profile()
    applied.append('frontend')
if BACKEND.exists():
    fix_backend_chat()
    applied.append('backend')
if not applied:
    raise RuntimeError('Nenhum estágio compatível do Docker foi encontrado.')

print(f'Ajustes da auditoria ponta a ponta aplicados com segurança em: {", ".join(applied)}.')
