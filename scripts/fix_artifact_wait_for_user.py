from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old in text:
        return text.replace(old, new, 1)
    if new in text:
        return text
    raise RuntimeError(f"{label}: trecho esperado não encontrado")


# Ajuste restrito ao gatilho automático: 1.200 caracteres apenas autorizam a
# avaliação. Se a resposta ainda pedir uma escolha ao usuário, nenhum arquivo é
# criado até a próxima mensagem. Pedidos explícitos de arquivo permanecem iguais.
path = Path('/app/app/services/artifact_decision.py')
text = path.read_text(encoding='utf-8')

text = text.replace(
    'os.getenv("DOMNAI_AUTO_ARTIFACT_MIN_CHARS", "800")',
    'os.getenv("DOMNAI_AUTO_ARTIFACT_MIN_CHARS", "1200")',
)

text = replace_once(
    text,
    '''def _spreadsheet_payload_is_useful(payload: dict) -> bool:
    sheets = payload.get("sheets") or []
    if sheets:
        return any(_table_is_useful(sheet.get("headers") or [], sheet.get("rows") or []) for sheet in sheets)
    return _table_is_useful(payload.get("headers") or [], payload.get("rows") or [])
''',
    '''def _spreadsheet_payload_is_useful(payload: dict) -> bool:
    sheets = payload.get("sheets") or []
    if sheets:
        return any(_table_is_useful(sheet.get("headers") or [], sheet.get("rows") or []) for sheet in sheets)
    return _table_is_useful(payload.get("headers") or [], payload.get("rows") or [])


def _answer_requires_user_response(answer: str) -> bool:
    """Impede entrega automática quando a resposta ainda aguarda decisão do usuário."""
    value = str(answer or "").strip()
    if not value:
        return False

    # A decisão pendente normalmente aparece no fechamento da resposta. Limitar
    # a análise ao trecho final evita bloquear relatórios por perguntas citadas
    # apenas como contexto em partes anteriores.
    tail = _normalize(value[-1800:])
    if "?" in value[-1800:]:
        return True

    pending_markers = (
        "me diga como prefere seguir",
        "diga como prefere seguir",
        "como prefere seguir",
        "qual opção você prefere",
        "qual opcao voce prefere",
        "qual você prefere",
        "qual voce prefere",
        "quer que eu",
        "você quer que eu",
        "voce quer que eu",
        "se desejar",
        "se quiser",
        "caso queira",
        "caso deseje",
        "posso montar",
        "posso preparar",
        "posso gerar",
        "posso fazer",
        "posso simular",
        "posso calcular",
        "posso comparar",
        "posso detalhar",
        "posso apresentar",
        "tem possibilidade de",
        "preciso saber",
        "preciso que você",
        "preciso que voce",
        "me informe",
        "informe se",
        "aguardo sua resposta",
        "aguardo sua confirmação",
        "aguardo sua confirmacao",
    )
    return any(marker in tail for marker in pending_markers)


def _artifact_title_without_extension(value: str) -> str:
    """Mantém o título sem extensão; o gerador acrescenta somente o tipo real."""
    title = str(value or "Documento DomnAI").strip()
    lowered = title.casefold()
    changed = True
    while changed:
        changed = False
        for suffix in (".pdf", ".xlsx", ".csv", "-pdf", "-xlsx", "-csv", "_pdf", "_xlsx", "_csv"):
            if lowered.endswith(suffix):
                title = title[:-len(suffix)].rstrip(" ._-–—")
                lowered = title.casefold()
                changed = True
                break
    return title or "Documento DomnAI"
''',
    'artifact_decision deterministic pending-response guard and title sanitizer',
)

text = replace_once(
    text,
    '- Quando `automatic_generation=true`, escolha o formato pela natureza principal da entrega e retorne `action=create`; nunca devolva `offer`.',
    '- Quando `automatic_generation=true`, o limite apenas autoriza a avaliação. Se a resposta atual ainda fizer uma pergunta, apresentar alternativas ou depender de uma escolha do usuário, retorne `action=none` e aguarde a próxima mensagem. Só retorne `action=create` quando o conteúdo estiver realmente concluído e não houver decisão pendente do usuário.',
    'artifact_decision pending-user-choice rule',
)

text = replace_once(
    text,
    '''    request_payload = {
        "operation": operation,
        "current_request": message,
        "completed_answer_for_current_request": answer,
        "automatic_generation": automatic_generation,
        "minimum_spreadsheet_columns": 4,
        "minimum_spreadsheet_rows": 10,
    }''',
    '''    if automatic_generation and _answer_requires_user_response(answer):
        return dict(_NONE)

    request_payload = {
        "operation": operation,
        "current_request": message,
        "completed_answer_for_current_request": answer,
        "automatic_generation": automatic_generation,
        "minimum_spreadsheet_columns": 4,
        "minimum_spreadsheet_rows": 10,
    }''',
    'artifact_decision stop before evaluation while user response is pending',
)

text = replace_once(
    text,
    '''        if automatic_generation:
            chosen_type = parsed.get("artifact_type")
            if chosen_type in {"xlsx", "csv"} and not _spreadsheet_payload_is_useful(parsed):
                chosen_type = "pdf"
            if chosen_type not in {"pdf", "xlsx", "csv"}:
                chosen_type = "pdf"
            parsed["action"] = "create"
            parsed["artifact_type"] = chosen_type
''',
    '''        if automatic_generation and parsed.get("action") == "create":
            chosen_type = parsed.get("artifact_type")
            if chosen_type in {"xlsx", "csv"} and not _spreadsheet_payload_is_useful(parsed):
                chosen_type = "pdf"
            if chosen_type not in {"pdf", "xlsx", "csv"}:
                chosen_type = "pdf"
            parsed["artifact_type"] = chosen_type
            parsed["title"] = _artifact_title_without_extension(parsed.get("title"))
        elif automatic_generation:
            parsed = dict(_NONE)
''',
    'artifact_decision do-not-force-create and sanitize title',
)

text = replace_once(
    text,
    '''        "title": str(payload.get("title") or "Documento DomnAI").strip()[:180],''',
    '''        "title": _artifact_title_without_extension(str(payload.get("title") or "Documento DomnAI"))[:180],''',
    'artifact_decision sanitize parsed title',
)

path.write_text(text, encoding='utf-8')
