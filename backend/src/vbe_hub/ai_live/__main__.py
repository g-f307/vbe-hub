import asyncio
import hashlib
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any
from uuid import UUID

from google import genai
from google.genai import types

from vbe_hub.adapters.ai.gemini import GeminiStructuredExtractor
from vbe_hub.adapters.ai.google_genai_client import GoogleGenAIClient
from vbe_hub.application.ai import ProviderError, ProviderErrorCode, StructuredExtractionRequest
from vbe_hub.application.ai.technical_sheet import SCHEMA_VERSION
from vbe_hub.infrastructure.settings import Settings

_FIXTURE = Path(__file__).with_name("live-synthetic-record.json")


async def run_live(
    settings: Settings,
    *,
    client_factory: Callable[..., Any] = genai.Client,
) -> dict[str, Any]:
    if settings.gemini_api_key is None or not settings.gemini_api_key.get_secret_value().strip():
        raise ProviderError(
            code=ProviderErrorCode.CONFIGURATION,
            message="GEMINI_API_KEY is required for the opt-in live command.",
            retryable=False,
        )

    normalized_data = json.loads(_FIXTURE.read_text(encoding="utf-8"))
    if normalized_data.get("synthetic") is not True:
        raise ProviderError(
            code=ProviderErrorCode.CONFIGURATION,
            message="The live command accepts only its bundled synthetic fixture.",
            retryable=False,
        )
    canonical = json.dumps(normalized_data, ensure_ascii=False, sort_keys=True).encode()
    request = StructuredExtractionRequest(
        record_id=UUID("00000000-0000-0000-0000-000000000008"),
        input_hash=hashlib.sha256(canonical).hexdigest(),
        normalized_data=normalized_data,
        schema_version=SCHEMA_VERSION,
        prompt_version="extract-v2",
        trace_id="live-synthetic-fixture-v1",
    )
    root_client = client_factory(
        api_key=settings.gemini_api_key.get_secret_value(),
        http_options=types.HttpOptions(
            api_version="v1",
            retry_options=types.HttpRetryOptions(attempts=1),
        ),
    )
    async with root_client.aio as async_client:
        extractor = GeminiStructuredExtractor(
            client=GoogleGenAIClient(models=async_client.models, model=settings.gemini_model),
            model=settings.gemini_model,
            timeout_seconds=settings.gemini_timeout_seconds,
            max_attempts=settings.gemini_max_attempts,
            max_input_chars=settings.gemini_max_input_chars,
            max_output_tokens=settings.gemini_max_output_tokens,
        )
        result = await extractor.extract(request)

    return {
        "provider": result.metadata.provider,
        "model": result.metadata.model,
        "schema_version": result.metadata.contract_version,
        "prompt_version": result.metadata.prompt_version,
        "duration_ms": result.metadata.duration_ms,
        "input_units": result.metadata.input_units,
        "output_units": result.metadata.output_units,
        "estimated_cost_usd": _estimated_cost(
            settings, result.metadata.input_units, result.metadata.output_units
        ),
        "technical_sheet": result.technical_sheet,
    }


def _estimated_cost(
    settings: Settings, input_units: int | None, output_units: int | None
) -> float | None:
    if (
        settings.gemini_input_usd_per_million is None
        or settings.gemini_output_usd_per_million is None
        or input_units is None
        or output_units is None
    ):
        return None
    cost = (
        input_units * settings.gemini_input_usd_per_million
        + output_units * settings.gemini_output_usd_per_million
    ) / 1_000_000
    return round(cost, 8)


async def _main() -> None:
    try:
        summary = await run_live(Settings())
    except ProviderError as error:
        raise SystemExit(str(error)) from None
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(_main())
