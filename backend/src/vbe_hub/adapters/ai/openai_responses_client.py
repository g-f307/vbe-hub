import json
from typing import Any, Protocol

from vbe_hub.adapters.ai.openai_extractor import (
    OpenAIClientRequest,
    OpenAIClientResponse,
    OpenAITransportError,
)


class AsyncResponses(Protocol):
    async def create(self, **kwargs: Any) -> Any: ...


class OpenAIResponsesClient:
    def __init__(self, *, responses: AsyncResponses, model: str) -> None:
        self._responses = responses
        self._model = model

    async def generate(self, request: OpenAIClientRequest) -> OpenAIClientResponse:
        try:
            response = await self._responses.create(
                model=self._model,
                input=request.contents,
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "technical_sheet",
                        "strict": True,
                        "schema": dict(request.response_schema),
                    }
                },
                reasoning={"effort": "none"},
                tools=[],
                store=False,
                max_output_tokens=request.max_output_tokens,
                timeout=request.timeout_seconds,
            )
        except Exception as error:
            raise OpenAITransportError(
                status_code=_status_code(error),
                error_code=_error_code(error),
                detail="OpenAI SDK request failed",
            ) from None

        output_text = getattr(response, "output_text", None)
        if not isinstance(output_text, str) or not output_text.strip():
            raise OpenAITransportError(
                status_code=422,
                error_code="missing_output",
                detail="OpenAI SDK response did not contain structured output",
            )
        try:
            payload = json.loads(output_text)
        except json.JSONDecodeError:
            raise OpenAITransportError(
                status_code=422,
                error_code="invalid_json",
                detail="OpenAI SDK response was not valid JSON",
            ) from None
        if not isinstance(payload, dict):
            raise OpenAITransportError(
                status_code=422,
                error_code="invalid_json_type",
                detail="OpenAI SDK response was not a JSON object",
            )

        usage = getattr(response, "usage", None)
        return OpenAIClientResponse(
            payload=payload,
            input_tokens=getattr(usage, "input_tokens", None),
            output_tokens=getattr(usage, "output_tokens", None),
        )


def _status_code(error: Exception) -> int | None:
    value = getattr(error, "status_code", None)
    return value if isinstance(value, int) else None


def _error_code(error: Exception) -> str | None:
    direct = getattr(error, "code", None)
    if isinstance(direct, str):
        return direct
    body = getattr(error, "body", None)
    if not isinstance(body, dict):
        return None
    nested = body.get("error")
    if isinstance(nested, dict) and isinstance(nested.get("code"), str):
        return nested["code"]
    value = body.get("code")
    return value if isinstance(value, str) else None
