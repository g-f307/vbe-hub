import json
from typing import Any, Protocol

from google.genai import types

from vbe_hub.adapters.ai.gemini import (
    GeminiClientRequest,
    GeminiClientResponse,
    GeminiTransportError,
)


class AsyncModels(Protocol):
    async def generate_content(self, **kwargs: Any) -> Any: ...


class GoogleGenAIClient:
    def __init__(self, *, models: AsyncModels, model: str) -> None:
        self._models = models
        self._model = model

    async def generate(self, request: GeminiClientRequest) -> GeminiClientResponse:
        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_json_schema=dict(request.response_schema),
            max_output_tokens=request.max_output_tokens,
            temperature=request.temperature,
            tools=None,
            http_options=types.HttpOptions(
                timeout=round(request.timeout_seconds * 1_000),
                retry_options=types.HttpRetryOptions(attempts=1),
            ),
        )
        try:
            response = await self._models.generate_content(
                model=self._model,
                contents=request.contents,
                config=config,
            )
        except Exception as error:
            status_code = getattr(error, "code", None)
            if not isinstance(status_code, int):
                status_code = getattr(error, "status_code", None)
            raise GeminiTransportError(
                status_code=status_code if isinstance(status_code, int) else None,
                detail="Gemini SDK request failed",
            ) from None

        payload = response.parsed
        if payload is None and isinstance(response.text, str):
            try:
                payload = json.loads(response.text)
            except json.JSONDecodeError:
                raise GeminiTransportError(
                    status_code=422,
                    detail="Gemini SDK response was not valid JSON",
                ) from None
        if not isinstance(payload, dict):
            raise GeminiTransportError(status_code=422, detail="Gemini SDK response was not JSON")

        usage = getattr(response, "usage_metadata", None)
        return GeminiClientResponse(
            payload=payload,
            input_tokens=getattr(usage, "prompt_token_count", None),
            output_tokens=getattr(usage, "candidates_token_count", None),
        )
