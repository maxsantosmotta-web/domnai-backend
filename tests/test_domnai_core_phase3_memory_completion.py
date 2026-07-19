from app.domnai_core.context_memory import ContextMemoryManager, MemoryScope
from app.domnai_core.contracts import ConversationRequest, ConversationResponse, HistoryMessage
from app.domnai_core.engine import ConversationEngine
from app.domnai_core.memory import InMemoryMemoryStore


def test_recent_correction_replaces_conflicting_preference():
    store = InMemoryMemoryStore()
    manager = ContextMemoryManager(store)
    scope = MemoryScope(user_id="u1", conversation_id="c1")

    manager.apply_update(scope, {"user": {"preferences": [{"key": "tone", "value": "formal", "source": "user"}]}})
    manager.apply_update(scope, {"user": {"corrections": [{"key": "tone", "value": "natural", "source": "user"}]}})

    memory = manager.load(scope)
    assert memory["user"]["preferences"] == []
    assert memory["user"]["corrections"][0]["value"] == "natural"


def test_expired_items_are_removed():
    store = InMemoryMemoryStore()
    manager = ContextMemoryManager(store, now_provider=lambda: 200.0)
    scope = MemoryScope(user_id="u1")

    manager.apply_update(scope, {"user": {"preferences": [{"value": "temporário", "source": "user", "expires_at": 100.0}]}})

    assert manager.load(scope)["user"]["preferences"] == []


def test_summary_is_persisted_from_long_history():
    store = InMemoryMemoryStore()
    manager = ContextMemoryManager(store)
    scope = MemoryScope(conversation_id="c1")
    history = tuple(HistoryMessage(role="user", content=f"Mensagem {i} com contexto") for i in range(20))

    summary = manager.persist_history_summary(scope, history, max_characters=300)

    loaded = manager.load(scope)
    assert loaded["context_summary"] == summary
    assert len(summary) <= 300


def test_natural_memory_instructions_are_present():
    manager = ContextMemoryManager(InMemoryMemoryStore())
    guidance = manager.build_usage_guidance({"user": {"preferences": [{"value": "natural", "source": "user"}]}})

    assert "não anuncie" in guidance.lower()
    assert "incerteza" in guidance.lower()


class CapturingProvider:
    def __init__(self):
        self.request = None

    def generate(self, request):
        self.request = request
        return ConversationResponse(text="ok", provider="stub", model="stub")


def test_engine_persists_summary_and_adds_natural_guidance():
    store = InMemoryMemoryStore()
    provider = CapturingProvider()
    engine = ConversationEngine(
        provider,
        memory_store=store,
        long_context_threshold=2,
        long_context_summary_characters=200,
    )
    history = (
        HistoryMessage(role="user", content="Prefiro respostas naturais."),
        HistoryMessage(role="assistant", content="Entendido."),
    )

    engine.respond(
        ConversationRequest(
            message="Continue",
            history=history,
            metadata={"user_id": "u1", "conversation_id": "c1", "scoped_memory": True},
        )
    )

    persisted = store.load("conversation:c1")
    assert persisted["summary"]
    assert provider.request.metadata["memory_usage_guidance"]
