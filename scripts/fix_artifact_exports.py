from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old in text:
        return text.replace(old, new, 1)
    if new in text:
        return text
    raise RuntimeError(f"{label}: trecho esperado não encontrado")


# 1) Decisor: preservar o conteúdo analítico anterior no PDF e aceitar múltiplas abas.
decision_path = Path('/app/app/services/artifact_decision.py')
decision = decision_path.read_text(encoding='utf-8')

decision = replace_once(
    decision,
    '''    "rows": [],
}''',
    '''    "rows": [],
    "sheets": [],
}''',
    'artifact_decision._NONE',
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


def _is_operational_artifact_answer(text: str) -> bool:
    normalized = _normalize(text)
    markers = (
        "vou preparar",
        "vou organizar",
        "vou gerar",
        "um momento",
        "aguarde",
        "já volto com",
        "ja volto com",
    )
    return len(str(text or "").strip()) < 500 and any(marker in normalized for marker in markers)


def _last_substantive_assistant_answer(history: list[dict]) -> str:
    for item in reversed(history):
        if str(item.get("role") or "").strip().lower() != "assistant":
            continue
        candidate = _remove_offer_from_answer(str(item.get("content") or "")).strip()
        if len(candidate) >= 200 and not _is_operational_artifact_answer(candidate):
            return candidate
    return ""
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

    if action == "create" and artifact_type in {"xlsx", "csv"} and not headers and not sheets:
        action = "offer"

    return {
        "action": action,
        "artifact_type": artifact_type,
        "title": str(payload.get("title") or "Documento DomnAI").strip()[:180],
        "sheet_name": str(payload.get("sheet_name") or "Dados").strip()[:31],
        "headers": headers,
        "rows": rows,
        "sheets": sheets,
    }''',
    'artifact_decision parse',
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
  "sheets":[{"sheet_name":"nome da aba","headers":["colunas"],"rows":[["valores"]]}]
}''',
    'artifact_decision schema',
)

decision = replace_once(
    decision,
    '''- Para XLSX/CSV com action=create, produza headers e rows completos usando apenas dados sustentados pela conversa e pela resposta. Não invente números.
- Prefira XLSX para uso humano e CSV quando o usuário pedir CSV ou quando o foco for importação de dados.''',
    '''- Para XLSX com action=create, quando o pedido mencionar vários documentos, categorias ou abas, produza `sheets` com TODAS as abas prometidas, cada uma com headers e rows completos. Não descarte itens após a primeira aba.
- Para XLSX de uma única tabela ou para CSV, produza headers e rows completos usando apenas dados sustentados pela conversa e pela resposta. Não invente números.
- Prefira XLSX para uso humano e CSV quando o usuário pedir CSV ou quando o foco for importação de dados.''',
    'artifact_decision spreadsheet rules',
)

decision = replace_once(
    decision,
    '''                "max_output_tokens": 1800,''',
    '''                "max_output_tokens": 5000,''',
    'artifact_decision token budget',
)

decision = replace_once(
    decision,
    '''        return _parse_decision(raw_text)
    except Exception:
        return dict(_NONE)''',
    '''        parsed = _parse_decision(raw_text)
        if parsed.get("action") == "create":
            source_answer = str(answer or "").strip()
            if parsed.get("artifact_type") == "pdf" and (_is_operational_artifact_answer(source_answer) or len(source_answer) < 200):
                source_answer = _last_substantive_assistant_answer(history) or source_answer
            parsed["source_answer"] = source_answer
        return parsed
    except Exception:
        return dict(_NONE)''',
    'artifact_decision source answer',
)

decision_path.write_text(decision, encoding='utf-8')


# 2) Gerador XLSX: suportar várias abas no mesmo workbook.
spreadsheet_path = Path('/app/app/services/spreadsheet_artifact.py')
spreadsheet = spreadsheet_path.read_text(encoding='utf-8')

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
                cell = worksheet.cell(row=row_index, column=column_index, value=value)
                cell.alignment = Alignment(vertical="top", wrap_text=True)

        for column_index, header in enumerate(headers, start=1):
            max_length = len(header)
            for row_index in range(2, min(len(rows) + 2, 302)):
                value = worksheet.cell(row=row_index, column=column_index).value
                max_length = max(max_length, len(str(value or "")))
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


# 3) Criação do artefato: usar múltiplas abas e rejeitar PDF operacional curto.
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
        operational_markers = ("vou preparar", "vou organizar", "vou gerar", "um momento", "aguarde")
        if len(clean_answer) < 200 and any(marker in clean_answer.casefold() for marker in operational_markers):
            raise ValueError("O conteúdo do relatório não foi localizado para gerar o PDF.")
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
