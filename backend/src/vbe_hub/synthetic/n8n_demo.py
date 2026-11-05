from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any

from openai import AsyncOpenAI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from vbe_hub.adapters.ai.openai_extractor import PROMPT_VERSION, OpenAIStructuredExtractor
from vbe_hub.adapters.ai.openai_responses_client import OpenAIResponsesClient
from vbe_hub.adapters.persistence.models import NormalizedRecordModel, RawRecordModel
from vbe_hub.adapters.persistence.repositories import SqlAlchemyExtractionRepository
from vbe_hub.application.ai import RelationKind, StructuredExtractionRequest, StructuredExtractor
from vbe_hub.application.ai.extraction import StructuredExtractionService
from vbe_hub.application.ai.technical_sheet import SCHEMA_VERSION
from vbe_hub.infrastructure.settings import get_settings
from vbe_hub.synthetic.demo import load_demo_scenario

_SCENARIOS = {
    "related": {
        "key": "dengue-compensa",
        "relation": "corroborates",
        "explanation": "Fontes sintéticas independentes descrevem o mesmo sinal demonstrativo.",
    },
    "incompatible": {
        "key": "leptospirose-jorge-teixeira",
        "relation": "unrelated",
        "explanation": "Local ou período incompatível exige manter os sinais separados.",
    },
    "ambiguous": {
        "key": "sarampo-cidade-nova",
        "relation": "related_context",
        "explanation": "Há contexto comum, mas a relação exige revisão profissional.",
    },
}

for _case_id in (
    "dengue-compensa",
    "sarampo-cidade-nova",
    "leptospirose-jorge-teixeira",
    "malaria-taruma",
    "doenca-diarreica-educandos",
    "influenza-parque-dez",
    "hepatite-a-colonia-antonio-aleixo",
    "chikungunya-ponta-negra",
    "meningite-zumbi",
    "febre-amarela-reserva-ducke",
):
    _SCENARIOS[_case_id] = {
        "key": _case_id,
        "relation": "corroborates",
        "explanation": "As duas fontes descrevem sinais compatíveis no mesmo local e período.",
    }


class N8nDemoService:
    def __init__(
        self,
        *,
        session: AsyncSession | None = None,
        extractor: StructuredExtractor | None = None,
        extraction_model: str | None = None,
    ) -> None:
        self._session = session
        self._extractor = extractor
        self._extraction_model = extraction_model

    async def run(self, *, scenario: str, mode: str) -> Mapping[str, Any]:
        definition = _SCENARIOS[scenario]
        if self._session is not None:
            return await self._run(self._session, scenario, mode, definition)

        settings = get_settings()
        engine = create_async_engine(settings.sqlalchemy_database_url, pool_pre_ping=True)
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        try:
            async with session_factory() as session:
                response = await self._run(session, scenario, mode, definition)
                await session.commit()
                return response
        finally:
            await engine.dispose()

    async def _run(
        self,
        session: AsyncSession,
        scenario: str,
        mode: str,
        definition: Mapping[str, str],
    ) -> Mapping[str, Any]:
        result = await load_demo_scenario(
            session,
            scenario_keys=frozenset({definition["key"]}),
            store_fixture_sheets=mode == "offline",
            relation_overrides={definition["key"]: RelationKind(definition["relation"])},
        )
        if mode == "online":
            result = await self._extract_online(session, definition["key"], result)
        return {
            "scenario": scenario,
            "mode": mode,
            "relation": definition["relation"],
            "relation_explanation": definition["explanation"],
            "signal_ids": list(result.signal_ids),
            "created": dict(result.created),
            "sources": [
                {
                    "source_kind": "media",
                    "external_id": f"demo:{definition['key']}:media",
                },
                {
                    "source_kind": "community",
                    "external_id": f"demo:{definition['key']}:community",
                },
            ],
            "review_notice": "Sugestão de IA; requer revisão humana.",
        }

    async def _extract_online(
        self,
        session: AsyncSession,
        scenario_key: str,
        result: Any,
    ) -> Any:
        extractor = self._extractor
        root_client = None
        settings = get_settings()
        model = self._extraction_model or settings.openai_model
        if extractor is None:
            if settings.openai_api_key is None or not settings.openai_api_key.get_secret_value():
                raise ValueError("OPENAI_API_KEY is required for online demo mode")
            root_client = AsyncOpenAI(
                api_key=settings.openai_api_key.get_secret_value(),
                timeout=settings.openai_timeout_seconds,
                max_retries=0,
            )
            extractor = OpenAIStructuredExtractor(
                client=OpenAIResponsesClient(responses=root_client.responses, model=model),
                model=model,
                timeout_seconds=settings.openai_timeout_seconds,
                max_attempts=settings.openai_max_attempts,
                max_input_chars=settings.openai_max_input_chars,
                max_output_tokens=settings.openai_max_output_tokens,
            )
        service = StructuredExtractionService(
            extractor=extractor,
            repository=SqlAlchemyExtractionRepository(session),
            provider="openai",
            model=model,
        )
        rows = list(
            (
                await session.execute(
                    select(NormalizedRecordModel)
                    .join(RawRecordModel, RawRecordModel.id == NormalizedRecordModel.raw_record_id)
                    .where(RawRecordModel.external_id.like(f"demo:{scenario_key}:%"))
                    .order_by(RawRecordModel.source_kind.desc())
                )
            ).scalars()
        )
        created = 0
        try:
            for row in rows:
                canonical = json.dumps(
                    row.normalized_data,
                    ensure_ascii=False,
                    separators=(",", ":"),
                    sort_keys=True,
                )
                response = await service.extract(
                    StructuredExtractionRequest(
                        record_id=row.id,
                        input_hash=hashlib.sha256(canonical.encode()).hexdigest(),
                        normalized_data=row.normalized_data,
                        schema_version=SCHEMA_VERSION,
                        prompt_version=PROMPT_VERSION,
                        trace_id=f"n8n-demo:{scenario_key}:{row.id}",
                    )
                )
                if not response.metadata.cache_hit:
                    created += 1
        finally:
            if root_client is not None:
                await root_client.close()
        counts = dict(result.created)
        counts["technical_sheets"] = created
        return type(result)(created=counts, signal_ids=result.signal_ids)


def build_demo_service() -> N8nDemoService:
    return N8nDemoService()
