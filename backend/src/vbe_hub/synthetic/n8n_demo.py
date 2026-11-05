from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any

from openai import AsyncOpenAI
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from vbe_hub.adapters.ai.openai_extractor import PROMPT_VERSION, OpenAIStructuredExtractor
from vbe_hub.adapters.ai.openai_relations import (
    PROMPT_VERSION as RELATION_PROMPT_VERSION,
)
from vbe_hub.adapters.ai.openai_relations import OpenAIRelationJudge
from vbe_hub.adapters.ai.openai_responses_client import OpenAIResponsesClient
from vbe_hub.adapters.persistence.relation_models import RelationAssessmentModel
from vbe_hub.adapters.persistence.relation_repository import (
    SqlAlchemyRelationAssessmentRepository,
)
from vbe_hub.adapters.persistence.repositories import SqlAlchemyExtractionRepository
from vbe_hub.application.ai import (
    RelationJudge,
    RelationKind,
    StructuredExtractionRequest,
    StructuredExtractor,
)
from vbe_hub.application.ai.extraction import StructuredExtractionService
from vbe_hub.application.ai.technical_sheet import SCHEMA_VERSION
from vbe_hub.application.correlation.relations import (
    RelationAssessmentRecord,
    RelationAssessmentService,
)
from vbe_hub.infrastructure.settings import get_settings
from vbe_hub.synthetic.demo import DemoLoadResult, load_demo_scenario, prepare_demo_scenario

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
        relation_judge: RelationJudge | None = None,
        extraction_model: str | None = None,
    ) -> None:
        self._session = session
        self._extractor = extractor
        self._relation_judge = relation_judge
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
        if mode == "online":
            result, assessment = await self._analyze_online(session, definition["key"])
            relation = assessment.relation
            explanation = assessment.justification
        else:
            result = await load_demo_scenario(
                session,
                scenario_keys=frozenset({definition["key"]}),
                store_fixture_sheets=True,
                relation_overrides={definition["key"]: RelationKind(definition["relation"])},
            )
            relation = RelationKind(definition["relation"])
            explanation = definition["explanation"]
        if relation is None or explanation is None:
            raise RuntimeError("demo relation analysis did not succeed")
        return {
            "scenario": scenario,
            "mode": mode,
            "relation": relation.value,
            "relation_explanation": explanation,
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

    async def _analyze_online(
        self,
        session: AsyncSession,
        scenario_key: str,
    ) -> tuple[DemoLoadResult, RelationAssessmentRecord]:
        prepared = await prepare_demo_scenario(session, scenario_key=scenario_key)
        extractor = self._extractor
        relation_judge = self._relation_judge
        root_client = None
        settings = get_settings()
        model = self._extraction_model or settings.openai_model
        if extractor is None or relation_judge is None:
            if settings.openai_api_key is None or not settings.openai_api_key.get_secret_value():
                raise ValueError("OPENAI_API_KEY is required for online demo mode")
            root_client = AsyncOpenAI(
                api_key=settings.openai_api_key.get_secret_value(),
                timeout=settings.openai_timeout_seconds,
                max_retries=0,
            )
            client = OpenAIResponsesClient(responses=root_client.responses, model=model)
            if extractor is None:
                extractor = OpenAIStructuredExtractor(
                    client=client,
                    model=model,
                    timeout_seconds=settings.openai_timeout_seconds,
                    max_attempts=settings.openai_max_attempts,
                    max_input_chars=settings.openai_max_input_chars,
                    max_output_tokens=settings.openai_max_output_tokens,
                )
            if relation_judge is None:
                relation_judge = OpenAIRelationJudge(
                    client=client,
                    model=model,
                    timeout_seconds=settings.openai_timeout_seconds,
                    max_input_chars=settings.openai_max_input_chars,
                )
        if extractor is None or relation_judge is None:
            raise RuntimeError("online demo providers were not configured")
        service = StructuredExtractionService(
            extractor=extractor,
            repository=SqlAlchemyExtractionRepository(session),
            provider="openai",
            model=model,
        )
        extraction_created = 0
        sheets: dict[Any, Mapping[str, Any]] = {}
        try:
            for row in prepared.records:
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
                    extraction_created += 1
                sheets[row.id] = response.technical_sheet
            relation_repository = SqlAlchemyRelationAssessmentRepository(session)
            relation_count_before = await session.scalar(
                select(func.count()).select_from(RelationAssessmentModel)
            )
            assessment = await RelationAssessmentService(
                judge=relation_judge,
                repository=relation_repository,
                relation_prompt_version=RELATION_PROMPT_VERSION,
            ).assess(
                left_id=prepared.records[0].id,
                right_id=prepared.records[1].id,
                left=sheets[prepared.records[0].id],
                right=sheets[prepared.records[1].id],
            )
            relation_count_after = await session.scalar(
                select(func.count()).select_from(RelationAssessmentModel)
            )
            result = await load_demo_scenario(
                session,
                scenario_keys=frozenset({scenario_key}),
                store_fixture_sheets=False,
                technical_sheet_overrides={scenario_key: sheets},
                relation_assessment_overrides={scenario_key: assessment},
            )
        finally:
            if root_client is not None:
                await root_client.close()
        counts = {
            key: prepared.created[key] + result.created[key] for key in prepared.created
        }
        counts["technical_sheets"] = extraction_created
        counts["relations"] = (relation_count_after or 0) - (relation_count_before or 0)
        return DemoLoadResult(created=counts, signal_ids=result.signal_ids), assessment


def build_demo_service() -> N8nDemoService:
    return N8nDemoService()
