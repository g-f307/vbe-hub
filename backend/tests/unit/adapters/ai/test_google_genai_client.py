from types import SimpleNamespace

import pytest

from vbe_hub.adapters.ai.gemini import GeminiClientRequest, GeminiTransportError
from vbe_hub.adapters.ai.google_genai_client import GoogleGenAIClient


class StubModels:
    def __init__(self, response: object = None, error: Exception | None = None) -> None:
        self.response = response
        self.error = error
        self.calls: list[dict[str, object]] = []

    async def generate_content(self, **kwargs: object) -> object:
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return self.response


class ApiFailure(Exception):
    def __init__(self, code: int) -> None:
        super().__init__("raw sensitive response")
        self.code = code


def request() -> GeminiClientRequest:
    return GeminiClientRequest(
        contents="synthetic fenced contents",
        response_schema={"type": "object", "additionalProperties": False},
        timeout_seconds=7,
        max_output_tokens=512,
    )


async def test_client_disables_sdk_retries_and_maps_parsed_response() -> None:
    response = SimpleNamespace(
        parsed={"record_nature": None},
        usage_metadata=SimpleNamespace(prompt_token_count=12, candidates_token_count=8),
    )
    models = StubModels(response=response)
    client = GoogleGenAIClient(models=models, model="gemini-3.5-flash-lite")

    result = await client.generate(request())

    assert result.payload == {"record_nature": None}
    assert result.input_tokens == 12
    assert result.output_tokens == 8
    call = models.calls[0]
    assert call["model"] == "gemini-3.5-flash-lite"
    assert call["contents"] == "synthetic fenced contents"
    assert call["config"].http_options.retry_options.attempts == 1
    assert call["config"].http_options.timeout == 7_000
    assert call["config"].tools is None


async def test_client_converts_sdk_error_without_exposing_details() -> None:
    client = GoogleGenAIClient(
        models=StubModels(error=ApiFailure(429)), model="gemini-3.5-flash-lite"
    )

    with pytest.raises(GeminiTransportError) as captured:
        await client.generate(request())

    assert captured.value.status_code == 429
    assert str(captured.value) == "Gemini SDK request failed"
    assert "sensitive" not in str(captured.value)


async def test_client_sanitizes_non_json_response() -> None:
    response = SimpleNamespace(parsed=None, text="not-json: sensitive provider output")
    client = GoogleGenAIClient(
        models=StubModels(response=response), model="gemini-3.5-flash-lite"
    )

    with pytest.raises(GeminiTransportError) as captured:
        await client.generate(request())

    assert captured.value.status_code == 422
    assert str(captured.value) == "Gemini SDK response was not valid JSON"
    assert "sensitive" not in str(captured.value)
