from app.services.metered_brain import MeteredBrainResult
from app.services.orchestrated_brain import (
    _specialized_engine,
    generate_orchestrated_response,
)


def base_result(text="Resposta-base"):
    return MeteredBrainResult(
        text=text,
        provider="test-provider",
        model="test-model",
        input_tokens=10,
        output_tokens=5,
        cached_input_tokens=0,
        diagnosis_state={"status": "kept"},
        timings={"generation_ms": 12},
    )


def test_operation_name_routes_to_labor_engine():
    assert _specialized_engine(
        plan={},
        operation="Cálculo de Rescisão Trabalhista",
        message="Preciso de ajuda.",
    ) == "labor_termination"


def test_natural_language_routes_to_labor_engine_without_frontend_operation():
    assert _specialized_engine(
        plan={},
        operation=None,
        message="Quero calcular minha rescisão.",
    ) == "labor_termination"


def test_orchestrator_plan_can_select_labor_engine():
    assert _specialized_engine(
        plan={"specialized_engine": "labor_termination"},
        operation=None,
        message="Analise este caso.",
    ) == "labor_termination"


def test_unrelated_operation_does_not_route_to_labor_engine():
    assert _specialized_engine(
        plan={"specialized_engine": None},
        operation="Análise Contratual",
        message="Revise as cláusulas deste contrato.",
    ) is None


def test_general_operation_uses_one_orchestrator_call_and_preserves_base_response(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    calls = []

    def fake_openai_request(_api_key, payload):
        calls.append(payload)
        return (
            '{"intent":"analisar contrato","response_mode":"analysis",'
            '"confidence_required":"high","requires_clarification":false,'
            '"essential_missing":[],"specialized_engine":null,'
            '"answer_focus":["riscos"],"material_risks":[],"style":"claro",'
            '"operation_complete":true,"offer_pdf":false,'
            '"pdf_sections":[],"chart_opportunities":[]}',
            {"input_tokens": 3, "output_tokens": 2},
        )

    monkeypatch.setattr("app.services.orchestrated_brain._openai_request", fake_openai_request)
    monkeypatch.setattr(
        "app.services.orchestrated_brain.generate_metered_response",
        lambda **_kwargs: base_result(),
    )

    result = generate_orchestrated_response(
        message="Analise este contrato.",
        history=[],
        operation="Análise Contratual",
        attachments=[],
        diagnosis_state=None,
    )

    assert len(calls) == 1
    assert result.text == "Resposta-base"
    assert result.provider == "orchestrated:test-provider"
    assert result.diagnosis_state == {"status": "kept"}
    assert result.input_tokens == 13
    assert result.output_tokens == 7
    assert result.timings["generation_ms"] == 12
    assert result.timings["orchestrator_ms"] >= 0


def test_orchestrator_failure_does_not_block_general_response(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(
        "app.services.orchestrated_brain._openai_request",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("orchestrator unavailable")),
    )
    monkeypatch.setattr(
        "app.services.orchestrated_brain.generate_metered_response",
        lambda **_kwargs: base_result("Resposta preservada"),
    )

    result = generate_orchestrated_response(
        message="Compare duas opções.",
        history=[],
        operation="Comparação",
        attachments=[],
        diagnosis_state={"status": "kept"},
    )

    assert result.text == "Resposta preservada"
    assert result.provider == "orchestrated:test-provider"
    assert result.diagnosis_state == {"status": "kept"}
    assert result.timings["orchestrator_ms"] >= 0


def test_without_openai_key_uses_existing_base_flow(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(
        "app.services.orchestrated_brain.generate_metered_response",
        lambda **_kwargs: base_result("Fluxo-base sem chave"),
    )

    result = generate_orchestrated_response(
        message="Olá",
        history=[],
        operation=None,
        attachments=[],
        diagnosis_state=None,
    )

    assert result.text == "Fluxo-base sem chave"
    assert result.provider == "test-provider"
