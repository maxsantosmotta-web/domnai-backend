import time

import pytest

from app.domnai_core import ConversationEngine, ConversationRequest, ConversationResponse
from app.domnai_core.tools import ToolCall, ToolPolicyError, ToolRegistry, ToolTimeoutError


class TwoToolProvider:
    def __init__(self) -> None:
        self.requests = []

    def generate(self, request: ConversationRequest) -> ConversationResponse:
        self.requests.append(request)
        if len(self.requests) == 1:
            return ConversationResponse(
                text="Executando duas ferramentas.",
                provider="stub",
                model="stub",
                metadata={
                    "response_id": "resp-1",
                    "tool_calls": (
                        {
                            "name": "calculate_expression",
                            "arguments": {"expression": "10 + 5"},
                            "call_id": "calc-1",
                        },
                        {
                            "name": "analyze_text",
                            "arguments": {"text": "Olá mundo. Segunda frase!"},
                            "call_id": "text-1",
                        },
                    ),
                },
            )
        results = request.metadata["last_tool_results"]
        return ConversationResponse(
            text=f"Cálculo {results[0]['output']['value']}; palavras {results[1]['output']['words']}.",
            provider="stub",
            model="stub",
        )


class SingleCallThenFinalProvider:
    def __init__(self, tool_name: str) -> None:
        self.tool_name = tool_name
        self.requests = []

    def generate(self, request: ConversationRequest) -> ConversationResponse:
        self.requests.append(request)
        if len(self.requests) == 1:
            return ConversationResponse(
                text="Executando.",
                provider="stub",
                model="stub",
                metadata={
                    "response_id": "resp-tool",
                    "tool_calls": (
                        {"name": self.tool_name, "arguments": {}, "call_id": "call-1"},
                    ),
                },
            )
        return ConversationResponse(text="Finalizado.", provider="stub", model="stub")


def _two_tool_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(
        "calculate_expression",
        lambda arguments: {"value": 15},
        risk_level="low",
        timeout_seconds=0.5,
        max_calls_per_turn=2,
    )
    registry.register(
        "analyze_text",
        lambda arguments: {"words": 4},
        risk_level="low",
        timeout_seconds=0.5,
        max_calls_per_turn=2,
    )
    return registry


def test_registry_exposes_and_validates_tool_policy():
    registry = ToolRegistry()
    registry.register(
        "safe",
        lambda arguments: {},
        risk_level="medium",
        timeout_seconds=1.5,
        max_calls_per_turn=2,
    )

    policy = registry.policy("safe")
    assert policy.risk_level == "medium"
    assert policy.timeout_seconds == 1.5
    assert policy.max_calls_per_turn == 2

    with pytest.raises(ValueError, match="risk_level"):
        ToolRegistry().register("bad", lambda arguments: {}, risk_level="critical")


def test_registry_times_out_tool_without_returning_late_result():
    registry = ToolRegistry()

    def slow(arguments):
        time.sleep(0.05)
        return {"done": True}

    registry.register("slow", slow, timeout_seconds=0.01)

    with pytest.raises(ToolTimeoutError, match="timeout"):
        registry.execute(ToolCall(name="slow", arguments={}))


def test_engine_executes_two_different_tools_in_same_turn_and_traces_each_step():
    provider = TwoToolProvider()
    engine = ConversationEngine(provider, tools=_two_tool_registry())

    response = engine.respond(ConversationRequest(message="Calcule e analise o texto"))

    assert response.text == "Cálculo 15; palavras 4."
    assert response.metadata["tool_calls_executed"] == 2
    assert response.metadata["tool_failures"] == 0
    assert [item["name"] for item in response.metadata["tool_trace"]] == [
        "calculate_expression",
        "analyze_text",
    ]
    assert all(item["status"] == "success" for item in response.metadata["tool_trace"])
    assert all(item["risk_level"] == "low" for item in response.metadata["tool_trace"])
    assert provider.requests[1].metadata["previous_response_id"] == "resp-1"


def test_disallowed_risk_is_recoverable_and_returned_to_model():
    registry = ToolRegistry()
    registry.register("sensitive", lambda arguments: {"ok": True}, risk_level="high")
    provider = SingleCallThenFinalProvider("sensitive")
    engine = ConversationEngine(provider, tools=registry, allowed_tool_risks=("low",))

    response = engine.respond(ConversationRequest(message="Execute"))

    assert response.text == "Finalizado."
    assert response.metadata["tool_failures"] == 1
    error = response.metadata["tool_results"][0]["output"]["error"]
    assert error["type"] == "ToolPolicyError"
    assert "não autorizado" in error["message"]
    assert response.metadata["tool_trace"][0]["risk_level"] == "high"


def test_global_tool_call_limit_blocks_oversized_batch_before_execution():
    provider = TwoToolProvider()
    engine = ConversationEngine(
        provider,
        tools=_two_tool_registry(),
        max_tool_calls_per_turn=1,
    )

    with pytest.raises(RuntimeError, match="Limite de 1 chamadas"):
        engine.respond(ConversationRequest(message="Execute duas"))
