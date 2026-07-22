from pathlib import Path

path = Path('/app/app/api/admin_users.py')
source = path.read_text(encoding='utf-8')

if 'from app.audit import record_audit_event' not in source:
    marker = 'from app.auth import require_authenticated_user\n'
    if marker not in source:
        raise RuntimeError('Importação de autenticação administrativa não localizada.')
    source = source.replace(marker, 'from app.audit import record_audit_event\n' + marker, 1)

endpoint = r'''

@router.delete('/{user_id}')
def delete_admin_user(
    user_id: str,
    session: dict = Depends(require_authenticated_user),
):
    admin_user_id, _admin_state = _require_admin(session)
    target_user_id = str(user_id or '').strip()
    if not target_user_id:
        raise HTTPException(status_code=422, detail='Usuário inválido.')
    if target_user_id == admin_user_id:
        raise HTTPException(status_code=409, detail='A conta administrativa atual não pode ser excluída por esta tela.')
    if _has_persisted_admin_access(target_user_id):
        raise HTTPException(status_code=409, detail='Contas administrativas não podem ser excluídas por esta tela.')

    secret = str(settings.clerk_secret_key or '').strip()
    if not secret:
        raise HTTPException(status_code=503, detail='CLERK_SECRET_KEY não configurada.')

    request = Request(
        f'{CLERK_USERS_URL}/{target_user_id}',
        headers={
            'Authorization': f'Bearer {secret}',
            'Accept': 'application/json',
            'User-Agent': 'DomnAI-Admin/1.0',
        },
        method='DELETE',
    )
    try:
        with urlopen(request, timeout=12) as response:
            response.read()
    except HTTPError as exc:
        detail = 'Não foi possível excluir o usuário no Clerk.'
        if exc.code == 404:
            detail = 'Usuário não encontrado no Clerk.'
        else:
            try:
                payload = json.loads(exc.read().decode('utf-8'))
                errors = payload.get('errors') if isinstance(payload, dict) else None
                if isinstance(errors, list) and errors:
                    detail = errors[0].get('long_message') or errors[0].get('message') or detail
                elif isinstance(payload, dict):
                    detail = payload.get('message') or detail
            except Exception:
                pass
        raise HTTPException(status_code=404 if exc.code == 404 else 502, detail=detail) from exc
    except (URLError, TimeoutError) as exc:
        raise HTTPException(status_code=502, detail='Não foi possível excluir o usuário no Clerk.') from exc

    with session_scope() as db:
        record_audit_event(
            db,
            user_id=admin_user_id,
            category='admin',
            module='Usuários',
            action='user_deleted',
            description=f'Usuário excluído manualmente pelo painel administrativo: {target_user_id}.',
            source='admin_users',
            source_key=f'user-delete:{target_user_id}',
        )

    return {'deleted': True, 'userId': target_user_id}
'''

if "@router.delete('/{user_id}')" not in source:
    source = source.rstrip() + endpoint + '\n'

path.write_text(source, encoding='utf-8')
print('Endpoint protegido de exclusão manual de usuários conectado ao painel administrativo.')
