import json

from app.domnai_core import ConversationEngine, ConversationRequest
from app.domnai_core.providers import OpenAIResponsesProvider
from app.domnai_core.tools import ToolRegistry


class FakeOpenAIResponsesProvider(OpenAIResponsesProvider):
    def __init__(self, responses):
        super().__init__(api_key="test-key", model="test-model")
        self.responses = list(responses)
        self.payloads = []

    def _request(self, payload: dict) -> dict:
        self.payloads.append(payload)
        return self.responses.pop(0)


def build_sum_registry():
    registry = ToolRegistry()
    registry.register(
        "sum",
        lambda arguments: {"value": arguments["a"] + arguments["b"]},
        description="Soma dois números.",
        parameters={
            "type": "object",
            "properties": {
                "a": {"type": "number"},
                "b": {"type": "number"},
            },
            "required": ["a", "b"],
            "additionalProperties": False,
        },
    )
    return registry


def test_registry_exposes_openai_function_definition():
    definition = build_sum_registry().definitions()[0]

    assert definition["type"] == "function"
    assert definition["name"] == "sum"
    assert definition["description"] == "Soma dois números."
    assert definition["parameters"]["required"] == ["a", "b"]
    assert definition["strict"] is True


def test_openai_provider_and_engine_complete_native_function_call_loop():
    provider = FakeOpenAIResponsesProvider(
        [
            {
                "id": "resp_tool",
                "output": [
                    {
                        "type": "function_call",
                        "name": "sum",
                        "call_id": "call_sum_1",
                        "arguments": json.dumps({"a": 2, "b": 3}),
                    }
                ],
                "usage": {"input_tokens": 10, "output_tokens": 4},
            },
            {
                "id": "resp_final",
                "output_text": "O resultado é 5.",
                "output": [],
                "usage": {"input_tokens": 6, "output_tokens": 5},
            },
        ]
    )
    engine = ConversationEngine(provider, tools=build_sum_registry())

    response = engine.respond(ConversationRequest(message="Quanto é 2 + 3?"))

    assert response.text == "O resultado é 5."
    assert response.metadata["tool_iterations"] == 1
    assert response.metadata["tool_results"][0] == {
        "name": "sum",
        "output": {"value": 5},
        "call_id": "call_sum_1",
    }

    first_payload, second_payload = provider.payloads
    assert first_payload["tools"][0]["name"] == "sum"
    assert first_payload["tool_choice"] == "auto"
    assert second_payload["previous_response_id"] == "resp_tool"
    assert second_payload["input"] == [
        {
            "type": "function_call_output",
            "call_id": "call_sum_1",
            "output": '{"value":5}',
        }
    ]


def test_openai_provider_returns_tool_call_metadata_before_execution():
    provider = FakeOpenAIResponsesProvider(
        [
            {
                "id": "resp_tool",
                "output": [
                    {
                        "type": "function_call",
                        "name": "sum",
                        "call_id": "call_123",
                        "arguments": "{\"a\":1,\"b\":4}",
                    }
                ],
                "usage": {},
            }
        ]
    )

    response = provider.generate(
        ConversationRequest(
            message="Some",
            metadata={"tool_definitions": build_sum_registry().definitions()},
        )
    )

    assert response.text == "Executando ferramenta solicitada."
    assert response.metadata["response_id"] == "resp_tool"
    assert response.metadata["tool_calls"] == (
        {
            "name": "sum",
            "arguments": {"a": 1, "b": 4},
            "call_id": "call_123",
        },
    )
