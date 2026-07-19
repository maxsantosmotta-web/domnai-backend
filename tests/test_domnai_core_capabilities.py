import pytest

from app.domnai_core import ConversationEngine, ConversationRequest, ConversationResponse
from app.domnai_core.memory import InMemoryMemoryStore
from app.domnai_core.persistence import InMemoryConversationRepository
from app.domnai_core.tools import ToolCall, ToolRegistry


class MemoryAwareProvider:
    def __init__(self) -> None:
        self.requests = []

    def generate(self, request: ConversationRequest) -> ConversationResponse:
        self.requests.append(request)
        return ConversationResponse(
            text="ok",
            provider="stub",
            model="stub",
            memory_update={"last_topic": request.message},
        )


class ToolLoopProvider:
    def __init__(self, *, repeat: bool = False) -> None:
        self.requests = []
        self.repeat = repeat

    def generate(self, request: ConversationRequest) -> ConversationResponse:
        self.requests.append(request)
        if len(self.requests) == 1 or self.repeat:
            return ConversationResponse(
                text="Consultando ferramenta.",
                provider="stub",
                model="stub",
                metadata={
                    "tool_calls": (
                        {"name": "sum", "arguments": {"a": 2, "b": 3}},
                    )
                },
            )
        return ConversationResponse(
            text=f"Resultado: {request.metadata['last_tool_results'][0]['output']['value']}",
            provider="stub",
            model="stub",
        )


class EndlessToolProvider:
    def __init__(self) -> None:
        self.counter = 0

    def generate(self, request: ConversationRequest) -> ConversationResponse:
        self.counter += 1
        return ConversationResponse(
            text="Continuando.",
            provider="stub",
            model="stub",
            metadata={
                "tool_calls": (
                    {"name": "sum", "arguments": {"a": self.counter, "b": 1}},
                )
            },
        )


def test_engine_loads_updates_and_saves_memory_by_conversation_id():
    provider = MemoryAwareProvider()
    memory = InMemoryMemoryStore()
    engine = ConversationEngine(provider, memory_store=memory)

    engine.respond(
        ConversationRequest(
            message="Primeiro assunto",
            memory={"user_name": "Max"},
            metadata={"conversation_id": "conv-1"},
        )
    )
    engine.respond(
        ConversationRequest(
            message="Segundo assunto",
            metadata={"conversation_id": "conv-1"},
        )
    )

    assert provider.requests[1].memory == {
        "user_name": "Max",
        "last_topic": "Primeiro assunto",
    }
    assert memory.load("conv-1")["last_topic"] == "Segundo assunto"


def test_engine_persists_each_completed_exchange():
    repository = InMemoryConversationRepository()
    engine = ConversationEngine(MemoryAwareProvider(), repository=repository)

    engine.respond(ConversationRequest(message="Olá", metadata={"conversation_id": "c"}))

    records = repository.records()
    assert len(records) == 1
    assert records[0].conversation_id == "c"
    assert records[0].response.text == "ok"


def test_tool_registry_only_executes_explicitly_registered_tools():
    registry = ToolRegistry()
    registry.register("sum", lambda arguments: {"value": arguments["a"] + arguments["b"]})

    result = registry.execute(ToolCall(name="sum", arguments={"a": 2, "b": 3}))

    assert registry.names() == ("sum",)
    assert result.output == {"value": 5}


def test_available_tools_are_exposed_as_context_without_automatic_execution():
    provider = MemoryAwareProvider()
    registry = ToolRegistry()
    registry.register("safe-tool", lambda arguments: arguments)
    engine = ConversationEngine(provider, tools=registry)

    engine.respond(ConversationRequest(message="Converse comigo"))

    assert provider.requests[0].metadata["available_tools"] == ("safe-tool",)


def test_engine_executes_tool_and_returns_final_provider_response():
    provider = ToolLoopProvider()
    registry = ToolRegistry()
    registry.register("sum", lambda arguments: {"value": arguments["a"] + arguments["b"]})
    engine = ConversationEngine(provider, tools=registry)

    response = engine.respond(ConversationRequest(message="Quanto é 2 + 3?"))

    assert response.text == "Resultado: 5"
    assert response.metadata["tool_iterations"] == 1
    assert response.metadata["tool_results"][0]["output"] == {"value": 5}
    assert len(provider.requests) == 2


def test_engine_blocks_repeated_identical_tool_call():
    provider = ToolLoopProvider(repeat=True)
    registry = ToolRegistry()
    registry.register("sum", lambda arguments: {"value": arguments["a"] + arguments["b"]})
    engine = ConversationEngine(provider, tools=registry)

    with pytest.raises(RuntimeError, match="Chamada repetida"):
        engine.respond(ConversationRequest(message="Repita indefinidamente"))


def test_engine_stops_when_tool_iteration_limit_is_reached():
    provider = EndlessToolProvider()
    registry = ToolRegistry()
    registry.register("sum", lambda arguments: {"value": arguments["a"] + arguments["b"]})
    engine = ConversationEngine(provider, tools=registry, max_tool_iterations=2)

    with pytest.raises(RuntimeError, match="Limite de iterações"):
        engine.respond(ConversationRequest(message="Continue usando ferramentas"))


def test_engine_rejects_negative_tool_iteration_limit():
    with pytest.raises(ValueError, match="não pode ser negativo"):
        ConversationEngine(MemoryAwareProvider(), max_tool_iterations=-1)
