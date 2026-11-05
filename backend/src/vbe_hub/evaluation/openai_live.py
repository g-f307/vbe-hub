from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from openai import AsyncOpenAI

from vbe_hub.adapters.ai.openai_extractor import OpenAIStructuredExtractor
from vbe_hub.adapters.ai.openai_responses_client import OpenAIResponsesClient
from vbe_hub.evaluation.command import assert_splits_are_disjoint, run_evaluation
from vbe_hub.infrastructure.settings import Settings


def require_openai_api_key(settings: Settings) -> str:
    if settings.openai_api_key is None:
        raise SystemExit("OPENAI_API_KEY is required for the opt-in OpenAI evaluation command.")
    value = settings.openai_api_key.get_secret_value().strip()
    if not value:
        raise SystemExit("OPENAI_API_KEY is required for the opt-in OpenAI evaluation command.")
    return value


async def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate technical-sheet extraction with OpenAI")
    parser.add_argument("--split", choices=("calibration", "evaluation"), required=True)
    parser.add_argument("--output", type=Path, default=Path("/data/reports"))
    args = parser.parse_args()
    settings = Settings()
    api_key = require_openai_api_key(settings)
    assert_splits_are_disjoint()

    async with AsyncOpenAI(
        api_key=api_key,
        timeout=settings.openai_timeout_seconds,
        max_retries=0,
    ) as root_client:
        extractor = OpenAIStructuredExtractor(
            client=OpenAIResponsesClient(
                responses=root_client.responses,
                model=settings.openai_model,
            ),
            model=settings.openai_model,
            timeout_seconds=settings.openai_timeout_seconds,
            max_attempts=settings.openai_max_attempts,
            max_input_chars=settings.openai_max_input_chars,
            max_output_tokens=settings.openai_max_output_tokens,
        )
        report = await run_evaluation(
            split=args.split,
            extractor=extractor,
            provider="openai",
            model=settings.openai_model,
            output_directory=args.output,
            input_usd_per_million=settings.openai_input_usd_per_million,
            output_usd_per_million=settings.openai_output_usd_per_million,
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
