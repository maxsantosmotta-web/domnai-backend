import pytest

from app.domnai_core.builtin_tools import build_builtin_tool_registry
from app.domnai_core.contracts import ConversationRequest, ConversationResponse
from app.domnai_core.engine import ConversationEngine


def test_calculator_executes_allowed_arithmetic():
    registry = build_builtin_tool_registry()
    result = registry.execute(
        __import__("app.domnai_core.tools", fromlist=["ToolCall"]).ToolCall(
            name="calculate_expression",
            arguments={"expression": "(2 + 3) * 4"},
        )
    )
    assert result.output == {"expression": "(2 + 3) * 4", "value": 20}


def test_calculator_rejects_code_and_unbounded_power():
    registry = build_builtin_tool_registry()
    ToolCall = __import__("app.domnai_core.tools", fromlist=["ToolCall"]).ToolCall

    with pytest.raises(ValueError, match="não permitida"):
        registry.execute(
            ToolCall(
                name="calculate_expression",
                arguments={"expression": "__import__('os').getcwd()"},
            )
        )
    with pytest.raises(ValueError, match="Expoente"):
        registry.execute(
            ToolCall(
                name="calculate_expression",
                arguments={"expression": "2 ** 100"},
            )
        )


def test_text_analysis_returns_deterministic_counts():
    registry = build_builtin_tool_registry()
    ToolCall = __import__("app.domnai_core.tools", fromlist=["ToolCall"]).ToolCall
    result = registry.execute(
        ToolCall(
            name="analyze_text",
            arguments={"text": "Olá mundo.\nTudo bem?"},
        )
    )
    assert result.output["words"] == 4
    assert result.output["lines"] == 2
    assert result.output["sentences"] == 2


class RecoverableToolProvider:
    def __init__(self) -> None:
        self.requests = []

    def generate(self, request: ConversationRequest) -> ConversationResponse:
        self.requests.append(request)
        if len(self.requests) == 1:
            return ConversationResponse(
                text="Vou calcular.",
                provider="stub",
                model="stub",
                metadata={
                    "response_id": "resp-1",
                    "tool_calls": (
                        {
                            "name": "calculate_expression",
                            "arguments": {"expression": "10 / 0"},
                            "call_id": "call-1",
                        },
                    ),
                },
            )
        result = request.metadata["last_tool_results"][0]
        assert result["status"] == "error"
        assert result["call_id"] == "call-1"
        assert result["output"]["error"]["type"] == "ValueError"
        return ConversationResponse(
            text="Não foi possível calcular porque a expressão divide por zero.",
            provider="stub",
            model="stub",
        )


def test_tool_failure_is_returned_to_model_and_conversation_recovers():
    provider = RecoverableToolProvider()
    engine = ConversationEngine(provider, tools=build_builtin_tool_registry())

    response = engine.respond(ConversationRequest(message="Quanto é 10 dividido por zero?"))

    assert "divide por zero" in response.text
    assert response.metadata["tool_failures"] == 1
    assert response.metadata["tool_results"][0]["status"] == "error"
    assert len(provider.requests) == 2
