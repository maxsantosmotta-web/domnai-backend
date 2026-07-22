from __future__ import annotations

from pathlib import Path


WORKER_PATH = Path("/app/app/services/chat_task_worker.py")


def replace_function(source: str, name: str, replacement: str) -> str:
    start = source.index(f"def {name}(")
    end = source.index("\n\ndef ", start + 1)
    return source[:start] + replacement.rstrip() + source[end:]


def patch_worker() -> None:
    source = WORKER_PATH.read_text(encoding="utf-8")

    if "from sqlalchemy.orm import aliased\n" not in source:
        source = source.replace(
            "from sqlalchemy import select, update\n",
            "from sqlalchemy import select, update\nfrom sqlalchemy.orm import aliased\n",
            1,
        )

    if "_claim_lock = threading.Lock()\n" not in source:
        source = source.replace(
            "_worker_lock = threading.Lock()\n",
            "_worker_lock = threading.Lock()\n_claim_lock = threading.Lock()\n",
            1,
        )

    claim_function = '''def _claim_next_task() -> str | None:
    with _claim_lock:
        with session_scope() as db:
            processing = aliased(ChatTask)
            processing_for_same_user = (
                select(processing.id)
                .where(
                    processing.user_id == ChatTask.user_id,
                    processing.status == "processing",
                )
                .correlate(ChatTask)
                .exists()
            )
            task = db.scalar(
                select(ChatTask)
                .where(
                    ChatTask.status == "queued",
                    ~processing_for_same_user,
                )
                .order_by(ChatTask.created_at.asc())
                .with_for_update(skip_locked=True)
                .limit(1)
            )
            if task is None:
                return None
            task.status = "processing"
            task.updated_at = _now()
            return task.id
'''
    source = replace_function(source, "_claim_next_task", claim_function)

    block_start = source.index("        sources: list[dict] = []\n", source.index("def _process_task("))
    block_end = source.index("        intelligence_started_at = time.perf_counter()\n", block_start)
    context_block = '''        sources: list[dict] = []
        contextual_history = list(history)
        context_blocks: list[str] = []

        user_name = str(payload.get("user_name") or "").strip()[:80]
        if user_name and operation and not history:
            context_blocks.append(
                "PERSONALIZAÇÃO INTERNA (não é fala do usuário): "
                f"o primeiro nome do usuário autenticado é {user_name}. "
                "Use-o somente se soar natural na abertura; não exponha este contexto."
            )

        if not payload.get("local_artifact_followup") and should_research_web(original_message):
            research_started_at = time.perf_counter()
            research = research_web(original_message)
            timings["research_ms"] = _elapsed_ms(research_started_at)
            sources = research.sources
            context_blocks.append(
                "EVIDÊNCIA EXTERNA VERIFICADA (não é fala do usuário):\n"
                + research.text
                + "\nUse somente fatos sustentados por esta evidência e nunca invente fontes ou URLs."
            )

        if context_blocks:
            contextual_history.append({
                "role": "assistant",
                "content": "CONTEXTO INTERNO SEPARADO DA MENSAGEM DO USUÁRIO:\n" + "\n\n".join(context_blocks),
            })
'''
    source = source[:block_start] + context_block + source[block_end:]

    old_call = '''        result = generate_orchestrated_response(
            message=message_for_brain,
            operation=operation,
            history=history,
            attachments=attachments,
            diagnosis_state=diagnosis_state,
        )
'''
    legacy_call = '''        result = generate_orchestrated_response(
            message=original_message,
            operation=operation,
            history=history,
            attachments=attachments,
            diagnosis_state=diagnosis_state,
            external_context=external_context,
        )
'''
    new_call = '''        result = generate_orchestrated_response(
            message=original_message,
            operation=operation,
            history=contextual_history,
            attachments=attachments,
            diagnosis_state=diagnosis_state,
        )
'''
    if old_call in source:
        source = source.replace(old_call, new_call, 1)
    elif legacy_call in source:
        source = source.replace(legacy_call, new_call, 1)
    elif new_call not in source:
        raise RuntimeError("chamada do orquestrador em formato desconhecido")

    required = (
        "processing_for_same_user",
        "should_research_web(original_message)",
        "history=contextual_history",
        "message=original_message",
        "CONTEXTO INTERNO SEPARADO DA MENSAGEM DO USUÁRIO",
    )
    for marker in required:
        if marker not in source:
            raise RuntimeError(f"integridade do worker ausente: {marker}")

    forbidden = (
        "should_research_web(original_message, operation)",
        "message=message_for_brain",
        "external_context=external_context",
    )
    for marker in forbidden:
        if marker in source:
            raise RuntimeError(f"mistura ou assinatura antiga permaneceu no worker: {marker}")

    WORKER_PATH.write_text(source, encoding="utf-8")


def patch_admin_user_deletion() -> None:
    path = Path('/app/app/api/admin_users.py')
    source = path.read_text(encoding='utf-8')
    if 'from app.audit import record_audit_event' not in source:
        marker = 'from app.auth import require_authenticated_user\n'
        if marker not in source:
            raise RuntimeError('Importação administrativa não localizada.')
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


def patch_document_disclaimers() -> None:
    disclaimer = (
        'Este documento organiza informações para apoio à decisão e não substitui a avaliação '
        'de profissional habilitado quando o tema exigir análise jurídica, contábil, médica, '
        'financeira ou técnica especializada.'
    )

    spreadsheet_path = Path('/app/app/services/spreadsheet_artifact.py')
    spreadsheet = spreadsheet_path.read_text(encoding='utf-8')
    if 'DOCUMENT_DISCLAIMER = (' not in spreadsheet:
        marker = 'from openpyxl.utils import get_column_letter\n\n'
        addition = "DOCUMENT_DISCLAIMER = (\n    'Este documento organiza informações para apoio à decisão e não substitui a avaliação '\n    'de profissional habilitado quando o tema exigir análise jurídica, contábil, médica, '\n    'financeira ou técnica especializada.'\n)\n\n"
        if marker not in spreadsheet:
            raise RuntimeError('Importações da planilha não localizadas.')
        spreadsheet = spreadsheet.replace(marker, marker + addition, 1)

    xlsx_marker = '''    for column_index, header in enumerate(clean_headers, start=1):
        max_length = len(header)
        for row_index in range(2, min(len(clean_rows) + 2, 302)):
            value = worksheet.cell(row=row_index, column=column_index).value
            max_length = max(max_length, len(str(value or "")))
        worksheet.column_dimensions[get_column_letter(column_index)].width = min(max(max_length + 2, 12), 42)

    output = io.BytesIO()
'''
    xlsx_replacement = '''    for column_index, header in enumerate(clean_headers, start=1):
        max_length = len(header)
        for row_index in range(2, min(len(clean_rows) + 2, 302)):
            value = worksheet.cell(row=row_index, column=column_index).value
            max_length = max(max_length, len(str(value or "")))
        worksheet.column_dimensions[get_column_letter(column_index)].width = min(max(max_length + 2, 12), 42)

    notice = workbook.create_sheet('Aviso')
    notice['A1'] = 'Aviso importante'
    notice['A1'].font = Font(bold=True)
    notice['A2'] = DOCUMENT_DISCLAIMER
    notice['A2'].alignment = Alignment(wrap_text=True, vertical='top')
    notice.column_dimensions['A'].width = 110
    notice.row_dimensions[2].height = 54

    output = io.BytesIO()
'''
    if "workbook.create_sheet('Aviso')" not in spreadsheet:
        if xlsx_marker not in spreadsheet:
            raise RuntimeError('Finalização do XLSX não localizada.')
        spreadsheet = spreadsheet.replace(xlsx_marker, xlsx_replacement, 1)

    csv_marker = '''    writer.writerow(clean_headers)
    writer.writerows(clean_rows)
    content = text.getvalue().encode("utf-8-sig")
'''
    csv_replacement = '''    writer.writerow(clean_headers)
    writer.writerows(clean_rows)
    writer.writerow([])
    writer.writerow(['Aviso importante', DOCUMENT_DISCLAIMER])
    content = text.getvalue().encode("utf-8-sig")
'''
    if "writer.writerow(['Aviso importante', DOCUMENT_DISCLAIMER])" not in spreadsheet:
        if csv_marker not in spreadsheet:
            raise RuntimeError('Finalização do CSV não localizada.')
        spreadsheet = spreadsheet.replace(csv_marker, csv_replacement, 1)
    spreadsheet_path.write_text(spreadsheet, encoding='utf-8')

    pdf_path = Path('/app/app/services/pdf_report.py')
    pdf = pdf_path.read_text(encoding='utf-8')
    old_notice = 'Este relatório organiza as informações fornecidas e não substitui avaliação profissional quando o tema exigir análise jurídica, contábil, médica, financeira ou técnica especializada.'
    if old_notice in pdf:
        pdf = pdf.replace(old_notice, disclaimer, 1)
    elif disclaimer not in pdf:
        raise RuntimeError('Aviso final do PDF não localizado.')
    pdf_path.write_text(pdf, encoding='utf-8')

    for chat_path in (Path('/app/app/api/chat.py'), WORKER_PATH):
        chat = chat_path.read_text(encoding='utf-8')
        old = 'Arquivo criado e enviado aqui no chat.'
        new = 'Arquivo criado e enviado aqui no chat. Este documento não substitui a avaliação de um profissional habilitado quando o tema exigir.'
        if old in chat and new not in chat:
            chat = chat.replace(old, new)
        chat_path.write_text(chat, encoding='utf-8')


patch_worker()
patch_admin_user_deletion()
patch_document_disclaimers()
print('Integridade conversacional, exclusão protegida de usuários e avisos de documentos aplicados.')
