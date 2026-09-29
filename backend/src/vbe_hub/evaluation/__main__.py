from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from google import genai
from google.genai import types

from vbe_hub.adapters.ai.gemini import GeminiStructuredExtractor
from vbe_hub.adapters.ai.google_genai_client import GoogleGenAIClient
from vbe_hub.evaluation.command import assert_splits_are_disjoint, run_evaluation
from vbe_hub.infrastructure.settings import Settings


async def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate technical-sheet extraction")
    parser.add_argument("--split", choices=("calibration", "evaluation"), required=True)
    parser.add_argument("--output", type=Path, default=Path("/data/reports"))
    args = parser.parse_args()
    settings = Settings()
    if settings.gemini_api_key is None or not settings.gemini_api_key.get_secret_value().strip():
        raise SystemExit("GEMINI_API_KEY is required for the opt-in evaluation command.")
    assert_splits_are_disjoint()
    root_client = genai.Client(
        api_key=settings.gemini_api_key.get_secret_value(),
        http_options=types.HttpOptions(
            api_version="v1", retry_options=types.HttpRetryOptions(attempts=1)
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
        report = await run_evaluation(
            split=args.split,
            extractor=extractor,
            provider="gemini",
            model=settings.gemini_model,
            output_directory=args.output,
            input_usd_per_million=settings.gemini_input_usd_per_million,
            output_usd_per_million=settings.gemini_output_usd_per_million,
        )
    print(
        json.dumps(
            {"identity": report["experiment"]["identity"], **report["execution"]},
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
