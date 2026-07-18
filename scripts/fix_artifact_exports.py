from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old in text:
        return text.replace(old, new, 1)
    if new in text:
        return text
    raise RuntimeError(f"{label}: trecho esperado não encontrado")


# Este script consolida a política final de artefatos no runtime depois dos
# patches anteriores do Docker. A escolha explícita do usuário prevalece; na
# geração automática, XLSX/CSV só passa com estrutura tabular realmente útil.
decision_path = Path('/app/app/services/artifact_decision.py')
decision = decision_path.read_text(encoding='utf-8')

decision = replace_once(
    decision,
    '''    "rows": [],
}''',
    '''    "rows": [],
    "sheets": [],
    "final_content": "",
}''',
    'artifact_decision._NONE',
)

decision = replace_once(
    decision,
    '''    return bool(operation and len(str(answer or "").strip()) >= 1000)''',
    '''    minimum_chars = max(120, int(os.getenv("DOMNAI_AUTO_ARTIFACT_MIN_CHARS", "800")))
    return bool(operation and len(str(answer or "").strip()) >= minimum_chars)''',
    'artifact_decision automatic threshold',
)

decision = replace_once(
    decision,
    '''def _clean_rows(value: Any, width: int) -> list[list[Any]]:
    if not isinstance(value, list) or width <= 0:
        return []
    rows: list[list[Any]] = []
    for raw_row in value[:5000]:
        if not isinstance(raw_row, list):
            continue
        row = list(raw_row[:width])
        if len(row) < width:
            row.extend([""] * (width - len(row)))
        rows.append(row)
    return rows
''',
    '''def _clean_rows(value: Any, width: int) -> list[list[Any]]:
    if not isinstance(value, list) or width <= 0:
        return []
    rows: list[list[Any]] = []
    for raw_row in value[:5000]:
        if not isinstance(raw_row, list):
            continue
        row = list(raw_row[:width])
        if len(row) < width:
            row.extend([""] * (width - len(row)))
        rows.append(row)
    return rows


def _clean_sheets(value: Any) -> list[dict]:
    if not isinstance(value, list):
        return []
    sheets: list[dict] = []
    used_names: set[str] = set()
    for index, raw_sheet in enumerate(value[:20], start=1):
        if not isinstance(raw_sheet, dict):
            continue
        headers = [str(item or "").strip()[:180] for item in (raw_sheet.get("headers") or [])[:50]]
        headers = [item for item in headers if item]
        if not headers:
            continue
        base_name = str(raw_sheet.get("sheet_name") or raw_sheet.get("name") or f"Dados {index}").strip()[:31] or f"Dados {index}"
        name = base_name
        suffix = 2
        while name.casefold() in used_names:
            tail = f" {suffix}"
            name = f"{base_name[:31-len(tail)]}{tail}"
            suffix += 1
        used_names.add(name.casefold())
        sheets.append({
            "sheet_name": name,
            "headers": headers,
            "rows": _clean_rows(raw_sheet.get("rows"), len(headers)),
        })
    return sheets


def _clean_final_content(value: Any) -> str:
    paragraphs = [part.strip() for part in str(value or "").split("\\n\\n") if part.strip()]
    operational_markers = (
        "vou preparar", "vou organizar", "vou gerar", "quer que eu", "posso gerar",
        "pronto!", "arquivo criado", "enviado aqui no chat", "um momento", "aguarde",
    )
    kept = [
        part for part in paragraphs
        if not any(marker in _normalize(part) for marker in operational_markers)
    ]
    return "\\n\\n".join(kept).strip()


def _table_is_useful(headers: list[Any], rows: list[Any]) -> bool:
    if len(headers or []) < 4:
        return False
    useful_rows = [
        row for row in (rows or [])
        if isinstance(row, list) and any(str(value or "").strip() for value in row)
    ]
    return len(useful_rows) >= 10


def _spreadsheet_payload_is_useful(payload: dict) -> bool:
    sheets = payload.get("sheets") or []
    if sheets:
        return any(_table_is_useful(sheet.get("headers") or [], sheet.get("rows") or []) for sheet in sheets)
    return _table_is_useful(payload.get("headers") or [], payload.get("rows") or [])
''',
    'artifact_decision helpers',
)

decision = replace_once(
    decision,
    '''    rows = _clean_rows(payload.get("rows"), len(headers))

    if action == "create" and artifact_type in {"xlsx", "csv"} and not headers:
        action = "offer"

    return {
        "action": action,
        "artifact_type": artifact_type,
        "title": str(payload.get("title") or "Documento DomnAI").strip()[:180],
        "sheet_name": str(payload.get("sheet_name") or "Dados").strip()[:31],
        "headers": headers,
        "rows": rows,
    }''',
    '''    rows = _clean_rows(payload.get("rows"), len(headers))
    sheets = _clean_sheets(payload.get("sheets"))
    final_content = _clean_final_content(payload.get("final_content"))

    if action == "create" and artifact_type in {"xlsx", "csv"} and not headers and not sheets:
        action = "none"
    if action == "create" and artifact_type == "pdf" and len(final_content) < 120:
        action = "none"

    return {
        "action": action,
        "artifact_type": artifact_type,
        "title": str(payload.get("title") or "Documento DomnAI").strip()[:180],
        "sheet_name": str(payload.get("sheet_name") or "Dados").strip()[:31],
        "headers": headers,
        "rows": rows,
        "sheets": sheets,
        "final_content": final_content,
    }''',
    'artifact_decision parse',
)

decision = replace_once(
    decision,
    '''    recent_history = history[-10:]
    request_payload = {
        "operation": operation,
        "current_message": message,
        "recent_history": recent_history,
        "completed_answer": answer,
    }''',
    '''    normalized_message = _normalize(message)
    explicit_request = _contains_any(normalized_message, _EXPLICIT_ARTIFACT_MARKERS)
    minimum_chars = max(120, int(os.getenv("DOMNAI_AUTO_ARTIFACT_MIN_CHARS", "800")))
    automatic_generation = bool(operation and not explicit_request and len(str(answer or "").strip()) >= minimum_chars)
    request_payload = {
        "operation": operation,
        "current_request": message,
        "completed_answer_for_current_request": answer,
        "automatic_generation": automatic_generation,
        "minimum_spreadsheet_columns": 4,
        "minimum_spreadsheet_rows": 10,
    }''',
    'artifact_decision isolated payload',
)

decision = replace_once(
    decision,
    '''  "sheet_name":"nome curto da aba",
  "headers":["colunas da planilha"],
  "rows":[["valores"]]
}''',
    '''  "sheet_name":"nome curto da aba quando houver somente uma",
  "headers":["colunas quando houver somente uma aba"],
  "rows":[["valores quando houver somente uma aba"]],
  "sheets":[{"sheet_name":"nome da aba","headers":["colunas"],"rows":[["valores"]]}],
  "final_content":"relatório final consolidado, obrigatório para PDF"
}''',
    'artifact_decision schema',
)

decision = replace_once(
    decision,
    '''- Não escolha formato por uma lista fixa de operações. Analise o pedido, o histórico e o conteúdo concluído.
- O formato explicitamente pedido na mensagem atual sempre tem prioridade sobre qualquer oferta anterior.''',
    '''- Analise SOMENTE `current_request` e `completed_answer_for_current_request`. Não use memória, histórico ou conversas anteriores.
- O formato explicitamente pedido na solicitação atual sempre tem prioridade e nunca pode ser trocado pela IA.
- Quando `automatic_generation=true`, escolha o formato pela natureza principal da entrega e retorne `action=create`; nunca devolva `offer`.
- Relatório, parecer, diagnóstico, análise narrativa, memória de cálculo explicativa, contrato, plano ou documento em que tabelas sejam apenas apoio deve ser PDF.
- XLSX/CSV automático só é permitido quando a entrega principal for uma base tabular editável, filtrável, calculável ou reutilizável e puder conter pelo menos 4 colunas coerentes e 10 linhas úteis reais.
- A presença isolada de uma tabela não transforma um relatório em planilha. Em dúvida entre relatório e planilha, escolha PDF.
- Não repita, fragmente ou invente informações para alcançar 4 colunas e 10 linhas.
- Quando a solicitação atual pedir criação, retorne `action=create` e entregue o conteúdo completo; nunca faça nova pergunta nem devolva `offer`.
- Para PDF, `final_content` deve conter somente o relatório final consolidado. Exclua confirmações, ofertas, avisos operacionais e frases como “vou preparar”, “quer que eu faça” ou “pronto”.''',
    'artifact_decision isolation rules',
)

decision = replace_once(
    decision,
    '''- Para XLSX/CSV com action=create, produza headers e rows completos usando apenas dados sustentados pela conversa e pela resposta. Não invente números.
- Prefira XLSX para uso humano e CSV quando o usuário pedir CSV ou quando o foco for importação de dados.''',
    '''- Para XLSX com action=create, quando o pedido exigir categorias, conjuntos ou abas distintas, produza `sheets` com TODAS as abas necessárias, cada uma com headers e rows completos.
- Para XLSX de uma única tabela ou CSV, produza headers e rows completos em estrutura tabular real. Não coloque listas inteiras dentro de uma única célula.
- Em geração automática de XLSX/CSV, produza no mínimo 4 colunas coerentes e 10 linhas úteis reais; se o conteúdo não sustentar isso, escolha PDF.
- Use apenas dados sustentados pela solicitação atual e pela resposta atual. Não invente números.
- Prefira XLSX para uso humano e CSV somente quando o usuário pedir CSV ou quando o foco inequívoco for importação de dados.''',
    'artifact_decision spreadsheet rules',
)

decision = replace_once(
    decision,
    '''                "max_output_tokens": 1800,''',
    '''                "max_output_tokens": 7000,''',
    'artifact_decision token budget',
)

decision = replace_once(
    decision,
    '''        return _parse_decision(raw_text)
    except Exception:
        return dict(_NONE)''',
    '''        parsed = _parse_decision(raw_text)

        normalized_message = _normalize(message)
        explicitly_csv = "csv" in normalized_message and explicit_request
        explicitly_xlsx = _explicit_spreadsheet_request(message) and not explicitly_csv
        explicitly_pdf = "pdf" in normalized_message and explicit_request
        if explicitly_csv:
            parsed["artifact_type"] = "csv"
        elif explicitly_xlsx:
            parsed["artifact_type"] = "xlsx"
        elif explicitly_pdf:
            parsed["artifact_type"] = "pdf"

        if automatic_generation:
            chosen_type = parsed.get("artifact_type")
            if chosen_type in {"xlsx", "csv"} and not _spreadsheet_payload_is_useful(parsed):
                chosen_type = "pdf"
            if chosen_type not in {"pdf", "xlsx", "csv"}:
                chosen_type = "pdf"
            parsed["action"] = "create"
            parsed["artifact_type"] = chosen_type

        if parsed.get("action") == "create":
            if parsed.get("artifact_type") == "pdf":
                parsed["source_answer"] = parsed.get("final_content") or str(answer or "").strip()
            else:
                parsed["source_answer"] = str(answer or "").strip()
        return parsed
    except Exception:
        return dict(_NONE)''',
    'artifact_decision validated selection',
)

decision_path.write_text(decision, encoding='utf-8')


spreadsheet_path = Path('/app/app/services/spreadsheet_artifact.py')
spreadsheet = spreadsheet_path.read_text(encoding='utf-8')
spreadsheet = replace_once(
    spreadsheet,
    '''def _safe_filename(value: str, extension: str) -> str:
    base = re.sub(r"[^A-Za-z0-9À-ÿ._-]+", "_", str(value or "planilha").strip())
    base = base.strip("._-") or "planilha"
    return f"{base[:120]}.{extension}"''',
    '''def _safe_filename(value: str, extension: str) -> str:
    base = re.sub(r"[^A-Za-z0-9À-ÿ._-]+", "_", str(value or "planilha").strip())
    base = re.sub(r"\\.(pdf|xlsx|csv)$", "", base, flags=re.IGNORECASE)
    base = base.strip("._-") or "planilha"
    return f"{base[:120]}.{extension}"''',
    'spreadsheet filename extension',
)
spreadsheet = replace_once(
    spreadsheet,
    '''def generate_csv(title: str, headers: list[str], rows: list[list[Any]]) -> GeneratedSpreadsheet:''',
    '''def generate_xlsx_sheets(title: str, sheets: list[dict]) -> GeneratedSpreadsheet:
    if not isinstance(sheets, list) or not sheets:
        raise ValueError("A planilha precisa ter ao menos uma aba.")

    workbook = Workbook()
    workbook.remove(workbook.active)
    used_names: set[str] = set()
    for index, sheet in enumerate(sheets[:20], start=1):
        headers, rows = _normalize_rows(sheet.get("headers") or [], sheet.get("rows") or [])
        base_name = (str(sheet.get("sheet_name") or f"Dados {index}").strip() or f"Dados {index}")[:31]
        name = base_name
        suffix = 2
        while name.casefold() in used_names:
            tail = f" {suffix}"
            name = f"{base_name[:31-len(tail)]}{tail}"
            suffix += 1
        used_names.add(name.casefold())
        worksheet = workbook.create_sheet(title=name)
        worksheet.freeze_panes = "A2"
        worksheet.auto_filter.ref = f"A1:{get_column_letter(len(headers))}{max(1, len(rows) + 1)}"
        for column_index, header in enumerate(headers, start=1):
            cell = worksheet.cell(row=1, column=column_index, value=header)
            cell.font = Font(bold=True)
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        for row_index, row in enumerate(rows, start=2):
            for column_index, value in enumerate(row, start=1):
                worksheet.cell(row=row_index, column=column_index, value=value).alignment = Alignment(vertical="top", wrap_text=True)
        for column_index, header in enumerate(headers, start=1):
            max_length = len(header)
            for row_index in range(2, min(len(rows) + 2, 302)):
                max_length = max(max_length, len(str(worksheet.cell(row=row_index, column=column_index).value or "")))
            worksheet.column_dimensions[get_column_letter(column_index)].width = min(max(max_length + 2, 12), 42)
    output = io.BytesIO()
    workbook.save(output)
    return GeneratedSpreadsheet(
        filename=_safe_filename(title, "xlsx"),
        mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        content=output.getvalue(),
    )


def generate_csv(title: str, headers: list[str], rows: list[list[Any]]) -> GeneratedSpreadsheet:''',
    'spreadsheet multi-sheet generator',
)
spreadsheet_path.write_text(spreadsheet, encoding='utf-8')


chat_path = Path('/app/app/api/chat.py')
chat = chat_path.read_text(encoding='utf-8')
chat = replace_once(
    chat,
    '''from app.services.spreadsheet_artifact import generate_csv, generate_xlsx''',
    '''from app.services.spreadsheet_artifact import generate_csv, generate_xlsx, generate_xlsx_sheets''',
    'chat import multi-sheet',
)
chat = replace_once(
    chat,
    '''    if artifact_type == "pdf":
        generated = generate_pdf_report(''',
    '''    if artifact_type == "pdf":
        clean_answer = str(answer or "").strip()
        if len(clean_answer) < 120:
            raise ValueError("O relatório final não foi consolidado para gerar o PDF.")
        generated = generate_pdf_report(''',
    'chat pdf validation',
)
chat = replace_once(
    chat,
    '''                "summary": answer,
                "sections": [{"title": "Resultado", "content": answer}],''',
    '''                "summary": clean_answer,
                "sections": [{"title": "Resultado", "content": clean_answer}],''',
    'chat pdf content',
)
chat = replace_once(
    chat,
    '''    elif artifact_type == "xlsx":
        generated = generate_xlsx(
            title,
            str(decision.get("sheet_name") or "Dados"),
            decision.get("headers") or [],
            decision.get("rows") or [],
        )''',
    '''    elif artifact_type == "xlsx":
        sheets = decision.get("sheets") or []
        if sheets:
            generated = generate_xlsx_sheets(title, sheets)
        else:
            generated = generate_xlsx(
                title,
                str(decision.get("sheet_name") or "Dados"),
                decision.get("headers") or [],
                decision.get("rows") or [],
            )''',
    'chat xlsx selection',
)
chat_path.write_text(chat, encoding='utf-8')
