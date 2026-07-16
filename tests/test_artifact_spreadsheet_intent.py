from app.services.artifact_decision import (
    _requires_artifact_decision,
    resolve_pending_artifact_acceptance,
)


def _previous_pdf_offer():
    return [{
        "role": "assistant",
        "content": (
            "Rotina completa organizada com etapas, frequência e observações detalhadas. "
            "O conteúdo está pronto para ser exportado e utilizado pelo usuário.\n\n"
            "Posso gerar este conteúdo em PDF e enviar o arquivo aqui no chat."
        ),
    }]


def test_explicit_spreadsheet_overrides_previous_pdf_offer():
    message = "Pode gerar um planilha desse arquivo"
    history = _previous_pdf_offer()

    assert resolve_pending_artifact_acceptance(message, history) is None
    assert _requires_artifact_decision(message, None, history, "Conteúdo organizado") is True


def test_natural_excel_request_is_recognized():
    assert _requires_artifact_decision(
        "Coloca isso no Excel para mim",
        None,
        [],
        "Conteúdo organizado",
    ) is True


def test_editable_table_request_is_recognized():
    assert _requires_artifact_decision(
        "Transforma isso numa tabela editável",
        None,
        [],
        "Conteúdo organizado",
    ) is True


def test_rows_and_columns_request_is_recognized():
    assert _requires_artifact_decision(
        "Organiza isso em linhas e colunas",
        None,
        [],
        "Conteúdo organizado",
    ) is True


def test_plain_acceptance_still_uses_previous_pdf_offer():
    resolved = resolve_pending_artifact_acceptance("Pode gerar", _previous_pdf_offer())

    assert resolved is not None
    assert resolved["artifact_type"] == "pdf"
