from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from openai import AsyncOpenAI

from vbe_hub.adapters.ai.openai_relations import OpenAIRelationJudge
from vbe_hub.adapters.ai.openai_responses_client import OpenAIResponsesClient
from vbe_hub.evaluation.related_signals import run_relation_quality_evaluation
from vbe_hub.infrastructure.settings import Settings


async def _run(args: argparse.Namespace) -> dict:
    settings = Settings()
    if settings.openai_api_key is None or not settings.openai_api_key.get_secret_value():
        raise SystemExit("OPENAI_API_KEY is required for the live related-signals evaluation")
    client = AsyncOpenAI(
        api_key=settings.openai_api_key.get_secret_value(),
        timeout=settings.openai_timeout_seconds,
        max_retries=0,
    )
    try:
        report = await run_relation_quality_evaluation(
            judge=OpenAIRelationJudge(
                client=OpenAIResponsesClient(
                    responses=client.responses, model=settings.openai_model
                ),
                model=settings.openai_model,
                timeout_seconds=settings.openai_timeout_seconds,
                max_input_chars=settings.openai_max_input_chars,
            ),
            cases_per_relation=args.cases_per_relation,
            seed=args.seed,
            input_usd_per_million=settings.openai_input_usd_per_million,
            output_usd_per_million=settings.openai_output_usd_per_million,
        )
    finally:
        await client.close()
    args.output.mkdir(parents=True, exist_ok=True)
    path = args.output / "related-signals-live-quality.json"
    path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the controlled OpenAI relation evaluation")
    parser.add_argument("--cases-per-relation", type=int, default=1)
    parser.add_argument("--seed", type=int, default=4040)
    parser.add_argument("--output", type=Path, default=Path("/data/reports"))
    args = parser.parse_args()
    report = asyncio.run(_run(args))
    print(
        json.dumps(
            {
                "dataset": report["dataset"],
                **report["quality"],
                "decision": report["decision"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
