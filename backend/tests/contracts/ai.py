from vbe_hub.application.ai import (
    EmbeddingProvider,
    EmbeddingRequest,
    RelationJudge,
    RelationRequest,
    StructuredExtractionRequest,
    StructuredExtractor,
)


async def assert_structured_extractor_contract(
    provider: StructuredExtractor, request: StructuredExtractionRequest
) -> None:
    first = await provider.extract(request)
    second = await provider.extract(request)

    assert first == second
    assert first.evidence
    assert first.metadata.provider
    assert first.metadata.contract_version


async def assert_embedding_provider_contract(
    provider: EmbeddingProvider, request: EmbeddingRequest
) -> None:
    first = await provider.embed(request)
    second = await provider.embed(request)

    assert first == second
    assert first.dimensions == request.expected_dimensions
    assert len(first.vector) == first.dimensions
    assert first.metadata.provider


async def assert_relation_judge_contract(
    provider: RelationJudge, request: RelationRequest
) -> None:
    first = await provider.judge(request)
    second = await provider.judge(request)

    assert first == second
    assert 0 <= first.confidence <= 1
    assert first.justification
    assert first.metadata.provider
