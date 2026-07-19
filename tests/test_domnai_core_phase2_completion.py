from app.domnai_core import ConversationEngine, ConversationRequest, ConversationResponse
from app.domnai_core.builtin_tools import build_builtin_tool_registry
from app.domnai_core.tools import ToolCall


class CorrelationProvider:
    def __init__(self) -> None:
        self.requests = []

    def generate(self, request: ConversationRequest) -> ConversationResponse:
        self.requests.append(request)
        if len(self.requests) == 1:
            return ConversationResponse(
                text="Usando ferramentas.",
                provider="stub",
                model="stub",
                metadata={
                    "response_id": "r1",
                    "tool_calls": (
                        {
                            "name": "normalize_text",
                            "arguments": {"text": "  DomnAI   ajuda\r\n\r\n pessoas  "},
                            "call_id": "normalize-1",
                        },
                        {
                            "name": "extract_keywords",
                            "arguments": {"text": "DomnAI ajuda pessoas. DomnAI apoia decisões.", "limit": 3},
                            "call_id": "keywords-1",
                        },
                    ),
                },
            )
        return ConversationResponse(text="Concluído.", provider="stub", model="stub")


def test_builtin_catalog_contains_safe_read_and_transform_tools():
    registry = build_builtin_tool_registry()
    assert registry.names() == (
        "analyze_text",
        "calculate_expression",
        "extract_keywords",
        "normalize_text",
    )
    assert all(registry.policy(name).risk_level == "low" for name in registry.names())


def test_normalize_text_is_deterministic_and_bounded():
    registry = build_builtin_tool_registry()
    result = registry.execute(
        ToolCall(
            name="normalize_text",
            arguments={"text": "  Olá   mundo\r\n\r\n\r\n teste  ", "collapse_lines": False},
        )
    )
    assert result.output["text"] == "Olá mundo\n\nteste"
    assert result.output["normalized_characters"] == len("Olá mundo\n\nteste")


def test_extract_keywords_orders_by_frequency_then_alphabetically():
    registry = build_builtin_tool_registry()
    result = registry.execute(
        ToolCall(
            name="extract_keywords",
            arguments={"text": "venda produto venda cliente produto estratégia", "limit": 3},
        )
    )
    assert result.output["keywords"] == [
        {"term": "produto", "count": 2},
        {"term": "venda", "count": 2},
        {"term": "cliente", "count": 1},
    ]


def test_request_id_is_generated_preserved_and_added_to_each_trace_item():
    provider = CorrelationProvider()
    engine = ConversationEngine(provider, tools=build_builtin_tool_registry())

    response = engine.respond(ConversationRequest(message="Analise e normalize"))

    request_id = response.metadata["request_id"]
    assert request_id
    assert provider.requests[0].metadata["request_id"] == request_id
    assert provider.requests[1].metadata["request_id"] == request_id
    assert response.metadata["tool_calls_executed"] == 2
    assert all(item["request_id"] == request_id for item in response.metadata["tool_trace"])
    assert [item["name"] for item in response.metadata["tool_trace"]] == [
        "normalize_text",
        "extract_keywords",
    ]


def test_supplied_request_id_is_not_replaced():
    provider = CorrelationProvider()
    engine = ConversationEngine(provider, tools=build_builtin_tool_registry())

    response = engine.respond(
        ConversationRequest(message="Analise", metadata={"request_id": "req-fixed"})
    )

    assert response.metadata["request_id"] == "req-fixed"
    assert all(item["request_id"] == "req-fixed" for item in response.metadata["tool_trace"])
