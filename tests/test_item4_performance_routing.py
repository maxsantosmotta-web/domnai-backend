from unittest.mock import patch

from app.services.artifact_decision import _requires_artifact_decision
from app.services.metered_brain import MeteredBrainResult
from app.services.orchestrated_brain import generate_orchestrated_response


def test_general_message_skips_orchestrator_request():
    generated = MeteredBrainResult(
        text="Resposta objetiva",
        provider="openai-memory",
        model="test",
        input_tokens=10,
        output_tokens=5,
        diagnosis_state=None,
        timings={"generation_ms": 20},
    )
    with patch(
        "app.services.orchestrated_brain.generate_metered_response",
        return_value=generated,
    ) as generator, patch(
        "app.services.orchestrated_brain._openai_request"
    ) as orchestrator:
        result = generate_orchestrated_response(
            message="Como posso organizar melhor meu dia?",
            history=[],
            operation=None,
            attachments=[],
            diagnosis_state=None,
        )

    generator.assert_called_once()
    orchestrator.assert_not_called()
    assert result.timings["orchestrator_ms"] == 0
    assert result.provider.startswith("direct:")


def test_short_common_answer_skips_artifact_ai():
    assert not _requires_artifact_decision(
        "Como organizar meu dia?",
        None,
        [],
        "Use três prioridades e revise no fim do dia.",
    )


def test_explicit_pdf_request_keeps_artifact_decision():
    assert _requires_artifact_decision(
        "Crie um PDF desse plano",
        None,
        [],
        "Plano concluído.",
    )


def test_long_operation_answer_can_still_offer_artifact():
    assert _requires_artifact_decision(
        "Monte meu plano",
        "Plano de Ação Empresarial",
        [],
        "x" * 1000,
    )
