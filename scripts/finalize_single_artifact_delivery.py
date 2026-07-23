from pathlib import Path
import re


ARTIFACT_DECISION_PATH = Path('/app/app/services/artifact_decision.py')
WORKER_PATH = Path('/app/app/services/chat_task_worker.py')
CHAT_API_PATH = Path('/app/app/api/chat.py')
PDF_REPORT_PATH = Path('/app/app/services/pdf_report.py')
DASHBOARD_PATH = Path('/frontend/src/Dashboard.jsx')


def write_python(path: Path, source: str) -> None:
    compile(source, str(path), 'exec')
    path.write_text(source, encoding='utf-8')


def patch_artifact_source_selection() -> None:
    source = ARTIFACT_DECISION_PATH.read_text(encoding='utf-8')

    accepted_offer_pattern = re.compile(
        r'def _accepted_offer\(value: str\) -> bool:\n.*?(?=\ndef _artifact_type_from_offer\()',
        flags=re.S,
    )
    accepted_offer_replacement = '''def _accepted_offer(value: str) -> bool:
    normalized = _normalize(value)
    if normalized in _ACCEPTANCE_EXACT or normalized == "eu quero":
        return True
    return any(
        normalized == phrase or normalized.startswith(f"{phrase} ")
        for phrase in _ACCEPTANCE_PHRASES
    )


'''
    source, accepted_count = accepted_offer_pattern.subn(
        accepted_offer_replacement,
        source,
        count=1,
    )
    if accepted_count != 1:
        raise RuntimeError('Função _accepted_offer não localizada em artifact_decision.py.')

    offered_type_pattern = re.compile(
        r'def _artifact_type_from_offer\(text: str\) -> str:\n.*?(?=\ndef _remove_offer_from_answer\()',
        flags=re.S,
    )
    offered_type_replacement = '''def _artifact_type_from_offer(text: str) -> str:
    normalized = _normalize(text)
    positions = {
        "pdf": min(
            (normalized.find(term) for term in ("pdf", "documento pdf", "arquivo pdf") if term in normalized),
            default=-1,
        ),
        "xlsx": min(
            (normalized.find(term) for term in ("planilha", "xlsx", "excel") if term in normalized),
            default=-1,
        ),
        "csv": min(
            (normalized.find(term) for term in ("csv", "arquivo csv") if term in normalized),
            default=-1,
        ),
    }
    offered = [(position, artifact_type) for artifact_type, position in positions.items() if position >= 0]
    if not offered:
        return "pdf"
    offered.sort(key=lambda item: item[0])
    return offered[0][1]


'''
    source, offered_type_count = offered_type_pattern.subn(
        offered_type_replacement,
        source,
        count=1,
    )
    if offered_type_count != 1:
        raise RuntimeError('Função _artifact_type_from_offer não localizada em artifact_decision.py.')

    last_answer_pattern = re.compile(
        r'def _last_completed_assistant_answer\(history: list\[dict\]\) -> str:\n.*?(?=\ndef _direct_document_decision\()',
        flags=re.S,
    )
    last_answer_replacement = '''def _last_completed_assistant_answer(history: list[dict]) -> str:
    for item in reversed(history):
        if str(item.get("role") or "").strip().lower() != "assistant":
            continue
        content = str(item.get("content") or "").strip()
        if not content:
            continue
        normalized = _normalize(content)
        invalid_artifact_source = (
            "openai respondeu http" in normalized
            or "nao foi possivel" in normalized
            or "nao consigo gerar arquivos" in normalized
            or "nao consigo criar o arquivo" in normalized
            or "nao consigo enviar arquivos" in normalized
            or "nao consigo gerar o pdf" in normalized
            or "texto final para copiar e colar" in normalized
            or "texto formatado para voce copiar" in normalized
            or "passo a passo para criar o pdf" in normalized
            or "sandbox mnt data" in normalized
            or "arquivo foi gerado" in normalized
            or "arquivo criado e enviado" in normalized
            or "pdf criado e enviado" in normalized
            or ("aqui esta o pdf" in normalized and "clique no link" in normalized)
        )
        if invalid_artifact_source:
            continue
        cleaned = _remove_offer_from_answer(content)
        if cleaned:
            return cleaned
    return ""


'''
    source, answer_count = last_answer_pattern.subn(
        last_answer_replacement,
        source,
        count=1,
    )
    if answer_count != 1:
        raise RuntimeError('Função _last_completed_assistant_answer não localizada em artifact_decision.py.')

    mature_helper = '''def _mature_conversation_pdf_offer(
    message: str,
    operation: str | None,
    history: list[dict],
    answer: str,
) -> dict | None:
    if not operation:
        return None

    # Pedido explícito ou aceitação de uma oferta anterior têm prioridade absoluta:
    # nesses casos o fluxo deve criar o arquivo, nunca devolver uma nova oferta.
    if detect_artifact_request(message, history) is not None or _accepted_offer(message):
        return None

    recent_text = _history_text(history, limit=24)
    if _contains_any(recent_text, _OFFER_MARKERS) or _contains_any(recent_text, _CREATED_MARKERS):
        return None

    user_turns = 1 + sum(
        1 for item in history[-24:]
        if str(item.get("role") or "").strip().lower() == "user"
        and len(str(item.get("content") or "").strip()) >= 15
    )
    assistant_turns = sum(
        1 for item in history[-24:]
        if str(item.get("role") or "").strip().lower() == "assistant"
        and len(str(item.get("content") or "").strip()) >= 80
    )
    normalized_answer = _normalize(answer)
    pending_markers = (
        "preciso saber", "preciso que voce", "por favor me diga", "me informe",
        "para afinar o diagnostico", "para continuar preciso", "faltam as seguintes",
        "responda as perguntas", "antes preciso saber",
    )
    completion_markers = (
        "recomendo", "causas mais provaveis", "passos iniciais", "proximos passos",
        "conclusao", "resultado", "orientacao", "analise final", "diagnostico",
        "plano de acao", "lista de verificacao",
    )

    conversation_is_mature = (
        user_turns >= 3
        and assistant_turns >= 2
        and len(recent_text) >= 700
        and len(str(answer or "").strip()) >= 450
        and any(marker in normalized_answer for marker in completion_markers)
        and not any(marker in normalized_answer for marker in pending_markers)
    )
    if not conversation_is_mature:
        return None

    return {
        "action": "offer",
        "artifact_type": "pdf",
        "title": str(operation).strip()[:180] or "Relatório consolidado",
        "sheet_name": "Dados",
        "headers": [],
        "rows": [],
    }


'''
    decide_anchor = 'def decide_artifact(\n'
    if 'def _mature_conversation_pdf_offer(' not in source:
        if decide_anchor not in source:
            raise RuntimeError('Entrada de decide_artifact não localizada.')
        source = source.replace(decide_anchor, mature_helper + decide_anchor, 1)

    entry_anchor = '''    direct = _direct_document_decision(message, operation, history)
'''
    entry_replacement = '''    mature_offer = _mature_conversation_pdf_offer(message, operation, history, answer)
    if mature_offer:
        return mature_offer

    direct = _direct_document_decision(message, operation, history)
'''
    if entry_replacement not in source:
        if entry_anchor not in source:
            raise RuntimeError('Início da decisão de artefato não localizado.')
        source = source.replace(entry_anchor, entry_replacement, 1)

    write_python(ARTIFACT_DECISION_PATH, source)


def patch_pdf_quality() -> None:
    source = PDF_REPORT_PATH.read_text(encoding='utf-8')

    if '\nimport re\n' not in source:
        source = source.replace('from io import BytesIO\n', 'from io import BytesIO\nimport re\n', 1)

    old_paragraph = '''def _paragraph_text(value: Any, limit: int = 10000) -> str:
    return escape(_safe_text(value, limit)).replace("\\n", "<br/>")
'''
    new_paragraph = '''def _paragraph_text(value: Any, limit: int = 10000) -> str:
    text = escape(_safe_text(value, limit))
    text = re.sub(r"\\*\\*(.+?)\\*\\*", r"<b>\\1</b>", text)
    return text.replace("\\n", "<br/>")


def _clean_document_body(value: Any, limit: int = 30000) -> str:
    text = _safe_text(value, limit)
    paragraphs = [part.strip() for part in re.split(r"\\n\\s*\\n", text) if part.strip()]
    removable_endings = (
        "quer que eu", "se quiser posso", "se quiser, posso", "deseja que eu",
        "posso ajudar", "quer que eu ajude", "ou prefere que eu",
    )
    while paragraphs:
        normalized = " ".join(paragraphs[-1].casefold().split())
        if not normalized.startswith(removable_endings):
            break
        paragraphs.pop()
    return "\\n\\n".join(paragraphs).strip()
'''
    if new_paragraph not in source:
        if old_paragraph not in source:
            raise RuntimeError('Conversão de texto do PDF não localizada.')
        source = source.replace(old_paragraph, new_paragraph, 1)

    title_anchor = '''    title = _safe_text(payload.get("title"), 180) or "Relatório DomnAI"
    operation = _safe_text(payload.get("operation"), 180)
    summary = _safe_text(payload.get("summary"), 20000)
'''
    title_replacement = '''    title = _safe_text(payload.get("title"), 180) or "Relatório DomnAI"
    operation = _safe_text(payload.get("operation"), 180)
    if title.casefold() in {"relatório consolidado", "relatorio consolidado", "documento domnai", "relatório domnai", "relatorio domnai"} and operation:
        title = operation
    if operation.casefold() == title.casefold():
        operation = ""
    summary = _clean_document_body(payload.get("summary"), 20000)
'''
    if title_replacement not in source:
        if title_anchor not in source:
            raise RuntimeError('Cabeçalho do relatório PDF não localizado.')
        source = source.replace(title_anchor, title_replacement, 1)

    body_anchor = '''        body = _safe_text(section.get("content"), 30000)
'''
    body_replacement = '''        body = _clean_document_body(section.get("content"), 30000)
'''
    if body_replacement not in source:
        if body_anchor not in source:
            raise RuntimeError('Conteúdo das seções do PDF não localizado.')
        source = source.replace(body_anchor, body_replacement, 1)

    write_python(PDF_REPORT_PATH, source)


def remove_backend_post_artifact_messages() -> None:
    worker = WORKER_PATH.read_text(encoding='utf-8')
    worker, worker_count = re.subn(
        r'^\s*"post_artifact_text"\s*:\s*.*?if artifacts else "",\s*\n',
        '',
        worker,
        count=1,
        flags=re.MULTILINE,
    )
    if '"post_artifact_text"' in worker:
        raise RuntimeError('A segunda mensagem posterior ainda existe no worker.')
    write_python(WORKER_PATH, worker)

    chat_api = CHAT_API_PATH.read_text(encoding='utf-8')
    chat_api, api_count = re.subn(
        r'^\s*"postArtifactText"\s*:\s*POST_ARTIFACT_TEXT if artifact else "",\s*\n',
        '',
        chat_api,
        count=1,
        flags=re.MULTILINE,
    )
    if '"postArtifactText"' in chat_api:
        raise RuntimeError('A segunda mensagem posterior ainda existe na API do chat.')
    write_python(CHAT_API_PATH, chat_api)

    if worker_count == 0 and api_count == 0:
        print('Avisos posteriores já estavam ausentes no backend.')


def remove_frontend_post_artifact_message() -> None:
    source = DASHBOARD_PATH.read_text(encoding='utf-8')
    if 'result.post_artifact_text' not in source and 'result.postArtifactText' not in source:
        return

    pattern = re.compile(
        r'(?P<indent>[ \t]*)setMessages\(\(current\) => \{\s*'
        r'const completed = current\.map\(\(message\) => \(.*?'
        r'const postText = String\(result\.post_artifact_text \|\| result\.postArtifactText \|\| [\'\"]{2}\)\.trim\(\);.*?'
        r'return \[\.\.\.completed, \{.*?\}\];\s*'
        r'\}\);',
        flags=re.DOTALL,
    )
    match = pattern.search(source)
    if not match:
        raise RuntimeError('Bloco de segunda mensagem posterior não localizado no Dashboard.jsx.')

    indent = match.group('indent')
    replacement = f'''{indent}setMessages((current) => current.map((message) => (
{indent}  message.taskId === taskId && message.role === 'assistant'
{indent}    ? {{
{indent}        ...message,
{indent}        text: result.reply || 'O DomnAI não retornou uma resposta em texto.',
{indent}        attachments: artifacts,
{indent}        processing: false,
{indent}        isError: false,
{indent}      }}
{indent}    : message
{indent})));'''
    source = source[:match.start()] + replacement + source[match.end():]

    if 'result.post_artifact_text' in source or 'result.postArtifactText' in source:
        raise RuntimeError('A segunda mensagem posterior permaneceu no frontend.')
    DASHBOARD_PATH.write_text(source, encoding='utf-8')


if ARTIFACT_DECISION_PATH.exists():
    patch_artifact_source_selection()
    patch_pdf_quality()
    remove_backend_post_artifact_messages()

if DASHBOARD_PATH.exists():
    remove_frontend_post_artifact_message()

print('Entrega finalizada: primeiro formato oferecido preservado sem alterar conteúdo, mensagem ou aviso.')
