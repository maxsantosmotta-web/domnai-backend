from app.services.artifact_decision import (
    _requires_artifact_decision,
    decide_artifact,
    resolve_pending_artifact_acceptance,
)


def test_long_answer_with_operation_does_not_trigger_artifact_decision():
    assert _requires_artifact_decision(
        message="Continue a análise.",
        operation="Plano de Ação Empresarial",
        history=[],
        answer="x" * 5000,
    ) is False


def test_explicit_pdf_request_triggers_artifact_decision():
    assert _requires_artifact_decision(
        message="Organize isso em PDF.",
        operation=None,
        history=[],
        answer="Conteúdo concluído.",
    ) is True


def test_explicit_spreadsheet_request_triggers_artifact_decision():
    assert _requires_artifact_decision(
        message="Coloque esses dados em uma planilha editável.",
        operation=None,
        history=[],
        answer="Conteúdo concluído.",
    ) is True


def test_simple_acceptance_without_previous_offer_does_not_create_file():
    assert resolve_pending_artifact_acceptance("Pode", []) is None
    assert decide_artifact(
        message="Pode",
        operation="Plano de Ação Empresarial",
        history=[],
        answer="Resposta normal.",
    )["action"] == "none"


def test_acceptance_after_real_offer_preserves_artifact_creation():
    source = (
        "Este é um conteúdo suficientemente completo para ser transformado em documento. "
        "Ele contém informações úteis, decisões e orientações já consolidadas para o usuário."
    )
    history = [{
        "role": "assistant",
        "content": source + "\n\nPosso organizar este resultado em um PDF.",
    }]

    decision = resolve_pending_artifact_acceptance("Sim, pode", history)

    assert decision is not None
    assert decision["action"] == "create"
    assert decision["artifact_type"] == "pdf"
    assert decision["source_answer"] == source


def test_existing_file_reuse_does_not_start_new_artifact_decision():
    history = [{"role": "assistant", "content": "PDF criado e enviado no chat."}]

    assert _requires_artifact_decision(
        message="Manda o link para baixar",
        operation=None,
        history=history,
        answer="",
    ) is False
