from __future__ import annotations

import asyncio
import hashlib
import json

from openai import AsyncOpenAI
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from vbe_hub.adapters.ai.openai_embeddings import OpenAIEmbeddingProvider
from vbe_hub.adapters.ai.openai_extractor import PROMPT_VERSION, OpenAIStructuredExtractor
from vbe_hub.adapters.ai.openai_relations import (
    PROMPT_VERSION as RELATION_PROMPT_VERSION,
)
from vbe_hub.adapters.ai.openai_relations import (
    OpenAIRelationJudge,
)
from vbe_hub.adapters.ai.openai_responses_client import OpenAIResponsesClient
from vbe_hub.adapters.persistence.embedding_repository import SqlAlchemyEmbeddingRepository
from vbe_hub.adapters.persistence.investigation_models import IndividualSignalModel
from vbe_hub.adapters.persistence.investigation_repository import (
    SqlAlchemySignalSuggestionRepository,
)
from vbe_hub.adapters.persistence.models import NormalizedRecordModel
from vbe_hub.adapters.persistence.related_signal_repository import (
    SqlAlchemyPreparedSignalSource,
)
from vbe_hub.adapters.persistence.relation_repository import (
    SqlAlchemyRelationAssessmentRepository,
)
from vbe_hub.adapters.persistence.repositories import SqlAlchemyExtractionRepository
from vbe_hub.application.ai import ProviderError, StructuredExtractionRequest
from vbe_hub.application.ai.embeddings import EmbeddingIndexService
from vbe_hub.application.ai.extraction import StructuredExtractionService
from vbe_hub.application.ai.technical_sheet import SCHEMA_VERSION
from vbe_hub.application.correlation.candidates import CandidatePolicy, GeographicLevel
from vbe_hub.application.correlation.precompute import RelatedSignalPrecomputer
from vbe_hub.application.correlation.relations import RelationAssessmentService
from vbe_hub.infrastructure.related_queue import RelatedSignalJob, RelatedSignalQueue
from vbe_hub.infrastructure.settings import Settings, get_settings


async def process_job(
    session: AsyncSession,
    job: RelatedSignalJob,
    *,
    settings: Settings,
    client: AsyncOpenAI,
) -> bool:
    row = (
        await session.execute(
            select(IndividualSignalModel, NormalizedRecordModel)
            .join(
                NormalizedRecordModel,
                NormalizedRecordModel.id == IndividualSignalModel.normalized_record_id,
            )
            .where(IndividualSignalModel.id == job.signal_id)
        )
    ).one_or_none()
    if row is None:
        return True
    signal, normalized = row
    canonical = json.dumps(
        normalized.normalized_data, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    )
    input_hash = hashlib.sha256(canonical.encode()).hexdigest()
    responses = OpenAIResponsesClient(responses=client.responses, model=settings.openai_model)
    extraction = await StructuredExtractionService(
        extractor=OpenAIStructuredExtractor(
            client=responses,
            model=settings.openai_model,
            timeout_seconds=settings.openai_timeout_seconds,
            max_attempts=settings.openai_max_attempts,
            max_input_chars=settings.openai_max_input_chars,
            max_output_tokens=settings.openai_max_output_tokens,
        ),
        repository=SqlAlchemyExtractionRepository(session),
        provider="openai",
        model=settings.openai_model,
    ).extract(
        StructuredExtractionRequest(
            record_id=normalized.id,
            input_hash=input_hash,
            normalized_data=normalized.normalized_data,
            schema_version=SCHEMA_VERSION,
            prompt_version=PROMPT_VERSION,
            trace_id=f"related:{signal.id}",
        )
    )
    await EmbeddingIndexService(
        provider=OpenAIEmbeddingProvider(
            embeddings=client.embeddings,
            model=settings.openai_embedding_model,
            timeout_seconds=settings.openai_timeout_seconds,
            max_input_chars=settings.openai_max_input_chars,
        ),
        repository=SqlAlchemyEmbeddingRepository(session),
        now=lambda: extraction.metadata.started_at,
    ).index(
        normalized_record_id=normalized.id,
        input_hash=input_hash,
        technical_sheet=extraction.technical_sheet,
    )
    result = await RelatedSignalPrecomputer(
        source=SqlAlchemyPreparedSignalSource(
            session, embedding_model=settings.openai_embedding_model
        ),
        suggestions=SqlAlchemySignalSuggestionRepository(session),
        assessor=RelationAssessmentService(
            judge=OpenAIRelationJudge(
                client=responses,
                model=settings.openai_model,
                timeout_seconds=settings.openai_timeout_seconds,
                max_input_chars=settings.openai_max_input_chars,
            ),
            repository=SqlAlchemyRelationAssessmentRepository(session),
            relation_prompt_version=RELATION_PROMPT_VERSION,
        ),
        policy=CandidatePolicy(30, GeographicLevel.DISTRICT, 0.65, 0.65),
        neighbor_limit=settings.related_neighbor_limit,
        candidate_limit=settings.related_candidate_limit,
        contract_version="related-signal-v1",
    ).process(signal.id)
    return result.failed == 0


async def _run() -> None:
    settings = get_settings()
    if settings.openai_api_key is None or not settings.openai_api_key.get_secret_value():
        await asyncio.Event().wait()
    engine = create_async_engine(settings.sqlalchemy_database_url, pool_pre_ping=True)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    redis = Redis.from_url(settings.redis_url.get_secret_value())
    queue = RelatedSignalQueue(
        redis=redis,
        capacity=settings.related_queue_capacity,
        pop_timeout_seconds=5,
        max_attempts=settings.openai_max_attempts,
    )
    client = AsyncOpenAI(
        api_key=settings.openai_api_key.get_secret_value(),
        timeout=settings.openai_timeout_seconds,
        max_retries=0,
    )
    try:
        while True:
            job = await queue.pop()
            if job is None:
                continue
            succeeded = False
            try:
                async with sessions() as session:
                    succeeded = await process_job(session, job, settings=settings, client=client)
                    await session.commit()
            except ProviderError:
                succeeded = False
            if succeeded or not await queue.retry(job):
                await queue.ack(job)
    finally:
        await client.close()
        await redis.aclose()
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(_run())
