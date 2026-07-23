from pathlib import Path
import re


DECISION_PATH = Path('/app/app/services/artifact_decision.py')
DELIVERY_PATH = Path('/app/app/domnai_core/artifact_delivery.py')
PDF_PATH = Path('/app/app/services/pdf_report.py')
WORKER_PATH = Path('/app/app/services/chat_task_worker.py')
CHAT_STATE_PATH = Path('/app/app/api/chat_state.py')

DELIVERY_REPLY = (
    'Pronto! Seu arquivo foi gerado com base nas informações desta conversa e '
    'está disponível logo abaixo. O conteúdo foi organizado para facilitar a leitura '
    'e a consulta. Ele também foi salvo automaticamente na Biblioteca.\n\n'
    'Importante: Este documento tem finalidade informativa e foi elaborado com base '
    'nas informações fornecidas durante esta conversa. Para decisões definitivas, '
    'recomenda-se sempre a validação por um profissional habilitado.'
)


def _write_compiled(path: Path, source: str) -> None:
    compile(source, str(path), 'exec')
    path.write_text(source, encoding='utf-8')


def patch_artifact_decision() -> None:
    source = DECISION_PATH.read_text(encoding='utf-8')

    helper = '''def _explicit_artifact_types(message: str) -> set[str]:
    normalized = _normalize(message)
    detected: set[str] = set()
    if _contains_any(normalized, _PDF_FORMAT_TERMS):
        detected.add("pdf")
    if _contains_any(normalized, _XLSX_FORMAT_TERMS):
        detected.add("xlsx")
    if _contains_any(normalized, _CSV_FORMAT_TERMS):
        detected.add("csv")
    return detected


'''
    anchor = 'def detect_artifact_request(message: str, history: list[dict] | None = None) -> str | None:\n'
    if 'def _explicit_artifact_types(' not in source:
        if anchor not in source:
            raise RuntimeError('Detector de artefato não localizado.')
        source = source.replace(anchor, helper + anchor, 1)

    old_direct = '''    artifact_type = detect_artifact_request(message, history)
    if artifact_type != "pdf":
        return None
    source_answer = _last_completed_assistant_answer(history)
'''
    new_direct = '''    explicit_types = _explicit_artifact_types(message)
    if explicit_types != {"pdf"}:
        return None
    source_answer = _last_completed_assistant_answer(history)
'''
    if old_direct in source:
        source = source.replace(old_direct, new_direct, 1)
    elif new_direct not in source:
        raise RuntimeError('Decisão direta de PDF não localizada.')

    source = source.replace(
        '        "title": str(operation or "Relatório consolidado").strip()[:180],\n',
        '        "title": "Relatório consolidado",\n',
        1,
    )

    decision_anchor = '''    direct = _direct_document_decision(message, operation, history)
'''
    choice_guard = '''    explicit_types = _explicit_artifact_types(message)
    normalized_message = _normalize(message)
    generic_document_request = (
        _contains_any(normalized_message, _GENERIC_DOCUMENT_TERMS)
        and _has_request_intent(normalized_message)
    )
    if len(explicit_types) > 1 or (not explicit_types and generic_document_request):
        return {
            "action": "offer",
            "artifact_type": "pdf",
            "title": "Relatório consolidado",
            "sheet_name": "Dados",
            "headers": [],
            "rows": [],
        }

    direct = _direct_document_decision(message, operation, history)
'''
    if choice_guard not in source:
        if decision_anchor not in source:
            raise RuntimeError('Entrada da decisão de artefato não localizada.')
        source = source.replace(decision_anchor, choice_guard, 1)

    _write_compiled(DECISION_PATH, source)


def patch_artifact_delivery() -> None:
    source = DELIVERY_PATH.read_text(encoding='utf-8')
    old_offer = "        return 'Posso gerar este conteúdo em PDF e enviar o arquivo aqui no chat.'"
    new_offer = (
        "        return 'Posso gerar este conteúdo em PDF. Se preferir, também posso preparar "
        "uma planilha XLSX. Qual formato você quer receber?'"
    )
    if old_offer in source:
        source = source.replace(old_offer, new_offer, 1)
    elif new_offer not in source:
        raise RuntimeError('Oferta de PDF não localizada.')

    old_operation = "            'operation': operation or 'Análise geral',"
    new_operation = "            'operation': '',"
    if old_operation in source:
        source = source.replace(old_operation, new_operation, 1)
    elif new_operation not in source:
        raise RuntimeError('Subtítulo do PDF não localizado.')

    _write_compiled(DELIVERY_PATH, source)


def patch_pdf_layout() -> None:
    source = PDF_PATH.read_text(encoding='utf-8')
    old_story = '''    story = [
        Paragraph(_paragraph_text(title, 180), styles["title"]),
        Paragraph(
            _paragraph_text(operation or "Relatório personalizado de apoio à decisão", 180),
            styles["subtitle"],
        ),
    ]
'''
    new_story = '''    story = [Paragraph(_paragraph_text(title, 180), styles["title"])]
    if operation:
        story.append(Paragraph(_paragraph_text(operation, 180), styles["subtitle"]))
'''
    if old_story in source:
        source = source.replace(old_story, new_story, 1)
    elif new_story not in source:
        raise RuntimeError('Cabeçalho do PDF não localizado.')
    _write_compiled(PDF_PATH, source)


def patch_worker_delivery_message() -> None:
    source = WORKER_PATH.read_text(encoding='utf-8')
    create_block_pattern = re.compile(
        r'(?P<start>        if decision\.get\("action"\) == "create":\n)'
        r'(?P<body>.*?)'
        r'(?P<offer>        elif decision\.get\("action"\) == "offer":)',
        flags=re.S,
    )
    match = create_block_pattern.search(source)
    if not match:
        raise RuntimeError('Bloco final de criação do artefato não localizado.')

    body = match.group('body')
    append_marker = '                artifacts.append(artifact)\n'
    append_index = body.find(append_marker)
    if append_index < 0:
        raise RuntimeError('Persistência do artefato criado não localizada no bloco final.')
    append_end = append_index + len(append_marker)

    exception_match = re.search(
        r'            except Exception(?: as \w+)?:\n.*\Z',
        body,
        flags=re.S,
    )
    if not exception_match:
        raise RuntimeError('Tratamento de falha da entrega não localizado no bloco final.')

    canonical_body = (
        body[:append_end]
        + '                reply = ' + repr(DELIVERY_REPLY) + '\n'
        + exception_match.group(0)
    )
    replacement = match.group('start') + canonical_body + match.group('offer')
    source = source[:match.start()] + replacement + source[match.end():]

    if source.count(DELIVERY_REPLY) != 1:
        raise RuntimeError('A mensagem final da entrega deve existir exatamente uma vez.')
    _write_compiled(WORKER_PATH, source)


def patch_chat_state_cleanup() -> None:
    source = CHAT_STATE_PATH.read_text(encoding='utf-8')
    old_block = '''        if not is_target:
            cleaned.append(item)
    return _deduplicate_task_messages(cleaned)
'''
    new_block = '''        normalized_text = _normalize_text(item.get("text")).casefold()
        standalone_artifact_notice = (
            str(item.get("role") or "").strip().lower() == "assistant"
            and not (item.get("attachments") or [])
            and "este documento foi gerado com base nas informações fornecidas durante esta conversa" in normalized_text
            and "profissional habilitado" in normalized_text
        )
        if not is_target and not standalone_artifact_notice:
            cleaned.append(item)
    return _deduplicate_task_messages(cleaned)
'''
    if old_block in source:
        source = source.replace(old_block, new_block, 1)
    elif new_block not in source:
        raise RuntimeError('Limpeza do estado do chat não localizada.')
    _write_compiled(CHAT_STATE_PATH, source)


patch_artifact_decision()
patch_artifact_delivery()
patch_pdf_layout()
patch_worker_delivery_message()
patch_chat_state_cleanup()
print('Fluxo final de conversa e artefato consolidado: escolha de formato, conteúdo atual, aviso único e subtítulo neutro.')
