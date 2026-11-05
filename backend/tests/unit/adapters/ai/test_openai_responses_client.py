import importlib
from types import SimpleNamespace

import pytest

from vbe_hub.adapters.ai.openai_extractor import OpenAIClientRequest


class StubResponses:
    def __init__(self, response: object = None, error: Exception | None = None) -> None:
        self.response = response
        self.error = error
        self.calls: list[dict[str, object]] = []

    async def create(self, **kwargs: object) -> object:
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return self.response


class ApiFailure(Exception):
    def __init__(self, status_code: int, error_code: str) -> None:
        super().__init__("raw response containing a secret")
        self.status_code = status_code
        self.body = {"error": {"code": error_code, "message": "secret account detail"}}


def request() -> OpenAIClientRequest:
    return OpenAIClientRequest(
        contents="synthetic fenced contents",
        response_schema={
            "type": "object",
            "properties": {"record_nature": {"type": ["string", "null"]}},
            "required": ["record_nature"],
            "additionalProperties": False,
        },
        timeout_seconds=7,
        max_output_tokens=512,
    )


async def test_client_sends_strict_schema_without_tools_and_maps_usage() -> None:
    module = importlib.import_module("vbe_hub.adapters.ai.openai_responses_client")
    responses = StubResponses(
        response=SimpleNamespace(
            output_text='{"record_nature": null}',
            usage=SimpleNamespace(input_tokens=12, output_tokens=8),
        )
    )
    client = module.OpenAIResponsesClient(responses=responses, model="gpt-6-luna")

    result = await client.generate(request())

    assert result.payload == {"record_nature": None}
    assert result.input_tokens == 12
    assert result.output_tokens == 8
    call = responses.calls[0]
    assert call["model"] == "gpt-6-luna"
    assert call["input"] == "synthetic fenced contents"
    assert call["max_output_tokens"] == 512
    assert call["timeout"] == 7
    assert call["tools"] == []
    assert call["store"] is False
    assert call["reasoning"] == {"effort": "none"}
    assert call["text"] == {
        "format": {
            "type": "json_schema",
            "name": "technical_sheet",
            "strict": True,
            "schema": request().response_schema,
        }
    }


async def test_client_preserves_error_classification_without_exposing_details() -> None:
    module = importlib.import_module("vbe_hub.adapters.ai.openai_responses_client")
    client = module.OpenAIResponsesClient(
        responses=StubResponses(error=ApiFailure(429, "credit_balance_exhausted")),
        model="gpt-6-luna",
    )

    with pytest.raises(module.OpenAITransportError) as captured:
        await client.generate(request())

    assert captured.value.status_code == 429
    assert captured.value.error_code == "credit_balance_exhausted"
    assert str(captured.value) == "OpenAI SDK request failed"
    assert "secret" not in str(captured.value)


@pytest.mark.parametrize("output_text", ["not-json: secret provider output", ""])
async def test_client_rejects_missing_or_invalid_json_without_leaking_output(
    output_text: str,
) -> None:
    module = importlib.import_module("vbe_hub.adapters.ai.openai_responses_client")
    client = module.OpenAIResponsesClient(
        responses=StubResponses(
            response=SimpleNamespace(
                output_text=output_text,
                usage=SimpleNamespace(input_tokens=12, output_tokens=8),
            )
        ),
        model="gpt-6-luna",
    )

    with pytest.raises(module.OpenAITransportError) as captured:
        await client.generate(request())

    assert captured.value.status_code == 422
    assert "secret" not in str(captured.value)
