from app.services.artifact_source import resolve_local_artifact_request


def test_direct_pdf_uses_previous_substantive_answer():
    history = [{
        "role": "assistant",
        "content": "Plano semanal completo com prioridades, horários, responsáveis e acompanhamento. " * 4,
    }]

    resolved = resolve_local_artifact_request("Manda o PDF", history)

    assert resolved is not None
    assert resolved["artifact_type"] == "pdf"
    assert "Plano semanal completo" in resolved["source_answer"]


def test_direct_pdf_skips_denial_message():
    history = [
        {
            "role": "assistant",
            "content": "Plano útil e detalhado com ações, horários, prioridades e responsáveis. " * 4,
        },
        {
            "role": "assistant",
            "content": "Não tenho como gerar ou enviar arquivos PDF diretamente. Posso preparar o texto.",
        },
    ]

    resolved = resolve_local_artifact_request("Gera o PDF", history)

    assert resolved is not None
    assert "Não tenho como gerar" not in resolved["source_answer"]
    assert "Plano útil e detalhado" in resolved["source_answer"]


def test_link_request_has_no_special_file_flow():
    history = [{
        "role": "assistant",
        "content": "Plano completo e detalhado. " * 10,
    }]

    assert resolve_local_artifact_request("Manda o link desse PDF", history) is None


def test_spreadsheet_request_is_not_changed_by_pdf_fix():
    history = [{
        "role": "assistant",
        "content": "Tabela completa com dias, horários e atividades. " * 5,
    }]

    assert resolve_local_artifact_request("Gera uma planilha", history) is None
