from app.services.diagnosis_memory import (
    diagnosis_extractor_instructions,
    empty_diagnosis_state,
    sanitize_diagnosis_state,
)
from app.services.orchestrated_brain import _simple_conversation_response


def test_confirmation_is_not_answered_without_contextual_intelligence():
    history = [{"role": "assistant", "content": "Você prefere o cenário conservador ou o agressivo?"}]
    assert _simple_conversation_response("Pode continuar", [], history) is None
    assert _simple_conversation_response("Perfeito", [], history) is None
    assert _simple_conversation_response("Certo", [], history) is None


def test_first_greeting_can_stay_local_but_greeting_inside_conversation_does_not_reset_context():
    assert _simple_conversation_response("Oi", [], []) is not None
    history = [{"role": "assistant", "content": "Já organizei os custos do projeto."}]
    assert _simple_conversation_response("Oi", [], history) is None


def test_farewell_after_productive_context_is_left_for_contextual_intelligence():
    short_history = [{"role": "assistant", "content": "Olá!"}]
    assert _simple_conversation_response("Até mais", [], short_history) == "Até mais!"

    productive_history = [
        {"role": "user", "content": "Quero estruturar meu projeto."},
        {"role": "assistant", "content": "Vamos definir o objetivo principal."},
        {"role": "user", "content": "O objetivo é lançar em agosto."},
        {"role": "assistant", "content": "Certo, já organizei as primeiras decisões."},
    ]
    assert _simple_conversation_response("Até mais", [], productive_history) is None


def test_universal_memory_preserves_general_decision_context():
    state = sanitize_diagnosis_state({
        "operation": "Abrir um Negócio do Zero",
        "current_topic": "Lanchonete regional",
        "user_goal": "Validar se o negócio é viável",
        "expected_delivery": "Plano de ação",
        "conversation_stage": "analyzing",
        "confirmed_facts": ["Orçamento inicial de R$ 20.000"],
        "user_constraints": ["Não ultrapassar o orçamento"],
        "user_preferences": ["Operação enxuta"],
        "alternatives": ["Loja física", "Delivery"],
        "decisions": ["Começar pelo delivery"],
        "corrections": ["O orçamento correto é R$ 20.000, não R$ 15.000"],
        "answered_questions": ["Orçamento inicial: R$ 20.000"],
    }, "Precificação Estratégica")

    assert state["operation"] == "Precificação Estratégica"
    assert state["current_topic"] == "Lanchonete regional"
    assert state["decisions"] == ["Começar pelo delivery"]
    assert state["corrections"]
    assert state["answered_questions"]


def test_memory_prompt_forbids_assistant_answer_as_confirmed_fact():
    instructions = diagnosis_extractor_instructions("Plano de Ação Empresarial")
    normalized = instructions.casefold()
    assert "resposta do domnai" in normalized
    assert "nunca" in normalized
    assert "fato confirmado" in normalized


def test_empty_memory_has_universal_fields():
    state = empty_diagnosis_state()
    for field in (
        "current_topic",
        "user_goal",
        "expected_delivery",
        "conversation_stage",
        "user_constraints",
        "user_preferences",
        "alternatives",
        "decisions",
        "corrections",
        "answered_questions",
    ):
        assert field in state
