from app.domnai_core import (
    ContextMemoryManager,
    ConversationEngine,
    ConversationRequest,
    ConversationResponse,
    HistoryMessage,
    InMemoryMemoryStore,
    MemoryScope,
)


class CapturingProvider:
    def __init__(self, memory_update=None):
        self.requests = []
        self.memory_update = memory_update

    def generate(self, request):
        self.requests.append(request)
        return ConversationResponse(
            text="ok",
            provider="stub",
            model="stub",
            memory_update=self.memory_update,
        )


def test_scoped_memory_separates_user_and_conversation():
    store = InMemoryMemoryStore()
    manager = ContextMemoryManager(store)
    scope = MemoryScope(user_id="user-1", conversation_id="conv-1")

    manager.apply_update(
        scope,
        {
            "user": {
                "preferences": ["Prefere respostas diretas"],
                "restrictions": [{"value": "Não alterar produção", "source": "user"}],
            },
            "conversation": {
                "decisions": ["Usar arquitetura source-first"],
                "summary": "Projeto DomnAI em reconstrução.",
            },
        },
    )

    loaded = manager.load(scope)
    assert loaded["user"]["preferences"][0]["value"] == "Prefere respostas diretas"
    assert loaded["conversation"]["decisions"][0]["value"] == "Usar arquitetura source-first"
    assert loaded["context_summary"] == "Projeto DomnAI em reconstrução."
    assert store.load("user:user-1")["restrictions"][0]["value"] == "Não alterar produção"
    assert store.load("conversation:conv-1")["summary"] == "Projeto DomnAI em reconstrução."


def test_unverified_model_facts_are_not_persisted():
    manager = ContextMemoryManager(InMemoryMemoryStore())
    normalized = manager.normalize_update(
        {
            "user": {
                "facts": [
                    {"value": "Usuário mora em Marte", "source": "model_inference"},
                    {"value": "Usuário informou que mora no Brasil", "source": "user"},
                ]
            }
        }
    )

    assert normalized["user"]["facts"] == [
        {"value": "Usuário informou que mora no Brasil", "source": "user"}
    ]


def test_memory_items_are_deduplicated_case_insensitively():
    store = InMemoryMemoryStore()
    manager = ContextMemoryManager(store)
    scope = MemoryScope(user_id="u")
    manager.apply_update(scope, {"user": {"preferences": ["Resposta curta"]}})
    manager.apply_update(scope, {"user": {"preferences": ["resposta curta", "Tom natural"]}})

    values = [item["value"] for item in manager.load(scope)["user"]["preferences"]]
    assert values == ["Resposta curta", "Tom natural"]


def test_long_history_summary_keeps_recent_context_with_limit():
    history = tuple(
        HistoryMessage(role="user" if index % 2 == 0 else "assistant", content=f"Mensagem {index}")
        for index in range(30)
    )
    summary = ContextMemoryManager.summarize_history(history, max_characters=150)

    assert len(summary) <= 150
    assert "Mensagem 29" in summary
    assert "Mensagem 0" not in summary


def test_engine_loads_scoped_memory_and_persists_structured_update():
    store = InMemoryMemoryStore()
    manager = ContextMemoryManager(store)
    scope = MemoryScope(user_id="user-9", conversation_id="conv-9")
    manager.apply_update(scope, {"user": {"preferences": ["Sem listas longas"]}})
    provider = CapturingProvider(
        memory_update={
            "user": {"corrections": ["Usar sempre o nome DomnAI"]},
            "conversation": {"decisions": ["Avançar para a Fase 3"]},
        }
    )
    engine = ConversationEngine(provider, memory_store=store)

    response = engine.respond(
        ConversationRequest(
            message="Continue",
            metadata={"user_id": "user-9", "conversation_id": "conv-9"},
        )
    )

    request = provider.requests[0]
    assert request.memory["user"]["preferences"][0]["value"] == "Sem listas longas"
    assert request.metadata["memory_scope"]["scoped"] is True
    assert response.metadata["request_id"]
    loaded = manager.load(scope)
    assert loaded["user"]["corrections"][0]["value"] == "Usar sempre o nome DomnAI"
    assert loaded["conversation"]["decisions"][0]["value"] == "Avançar para a Fase 3"


def test_engine_generates_bounded_summary_only_for_long_context():
    provider = CapturingProvider()
    engine = ConversationEngine(
        provider,
        long_context_threshold=4,
        long_context_summary_characters=120,
    )
    history = tuple(
        HistoryMessage(role="user", content=f"Contexto importante {index}")
        for index in range(6)
    )

    engine.respond(ConversationRequest(message="Responda", history=history))

    request = provider.requests[0]
    assert request.metadata["context_summary_generated"] is True
    assert len(request.memory["recent_context_summary"]) <= 120


def test_legacy_conversation_memory_behavior_remains_compatible_without_user_scope():
    store = InMemoryMemoryStore()
    store.save("conv-legacy", {"topic": "antigo"})
    provider = CapturingProvider(memory_update={"next": "novo"})
    engine = ConversationEngine(provider, memory_store=store)

    engine.respond(
        ConversationRequest(message="Olá", metadata={"conversation_id": "conv-legacy"})
    )

    assert provider.requests[0].memory == {"topic": "antigo"}
    assert store.load("conv-legacy") == {"topic": "antigo", "next": "novo"}
