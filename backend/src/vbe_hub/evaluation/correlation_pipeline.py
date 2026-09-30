from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from itertools import combinations
from typing import Any
from uuid import UUID

from vbe_hub.application.ai import (
    EmbeddingProvider,
    EmbeddingRequest,
    ProviderError,
    RelationJudge,
)
from vbe_hub.application.ai.embeddings import EMBEDDING_DIMENSIONS, build_embedding_text
from vbe_hub.application.correlation.candidates import (
    CandidateInput,
    CandidatePolicy,
    CandidateSelector,
)
from vbe_hub.application.correlation.relations import (
    RelationAssessmentRecord,
    RelationAssessmentService,
    RelationMethod,
)
from vbe_hub.evaluation.correlation_metrics import (
    CorrelationCase,
    CorrelationMetrics,
    OperationalSample,
    evaluate_correlation,
)
from vbe_hub.evaluation.relation_dataset import RelationPairInput


@dataclass(frozen=True, slots=True)
class CorrelationEvaluationRecord:
    record_id: UUID
    technical_sheet: dict[str, Any]


@dataclass(frozen=True, slots=True)
class CorrelationPrediction:
    left_id: str
    right_id: str
    selected: bool
    predicted_relation: str | None
    exclusion_reason: str | None
    failure_code: str | None
    operation: OperationalSample | None
    sent_to_provider: bool = False
    confidence: float | None = None
    justification: str | None = None


class _MemoryRelationRepository:
    def __init__(self) -> None:
        self.records: dict[str, RelationAssessmentRecord] = {}

    async def get(self, cache_key: str) -> RelationAssessmentRecord | None:
        return self.records.get(cache_key)

    async def save(self, record: RelationAssessmentRecord) -> None:
        self.records[record.cache_key] = record


async def predict_correlations(
    records: list[CorrelationEvaluationRecord],
    *,
    embedding_provider: EmbeddingProvider,
    judge: RelationJudge,
    policy: CandidatePolicy,
    input_usd_per_million: float | None = None,
    output_usd_per_million: float | None = None,
) -> list[CorrelationPrediction]:
    vectors: dict[UUID, tuple[float, ...]] = {}
    for record in records:
        text = build_embedding_text(record.technical_sheet)
        digest = hashlib.sha256(text.encode()).hexdigest()
        result = await embedding_provider.embed(
            EmbeddingRequest(record.record_id, digest, text, EMBEDDING_DIMENSIONS)
        )
        vectors[record.record_id] = result.vector

    service = RelationAssessmentService(judge=judge, repository=_MemoryRelationRepository())
    selector = CandidateSelector(policy)
    predictions: list[CorrelationPrediction] = []
    for left, right in combinations(records, 2):
        decision = selector.select(
            anchor_id=left.record_id,
            anchor_sheet=left.technical_sheet,
            neighbors=[
                CandidateInput(
                    right.record_id,
                    _cosine(vectors[left.record_id], vectors[right.record_id]),
                    right.technical_sheet,
                )
            ],
        ).decisions[0]
        if not decision.included:
            predictions.append(
                CorrelationPrediction(
                    str(left.record_id),
                    str(right.record_id),
                    False,
                    None,
                    next(
                        (reason for reason in decision.reasons if reason != "candidate_selected"),
                        "unknown",
                    ),
                    None,
                    None,
                )
            )
            continue
        try:
            assessment = await service.assess(
                left_id=left.record_id,
                right_id=right.record_id,
                left=left.technical_sheet,
                right=right.technical_sheet,
            )
        except ProviderError as error:
            predictions.append(
                CorrelationPrediction(
                    str(left.record_id),
                    str(right.record_id),
                    True,
                    None,
                    None,
                    error.code.value,
                    _operation(error.metadata, input_usd_per_million, output_usd_per_million),
                    sent_to_provider=True,
                )
            )
            continue
        predictions.append(
            CorrelationPrediction(
                str(left.record_id),
                str(right.record_id),
                True,
                assessment.relation.value if assessment.relation else None,
                None,
                None,
                _operation(assessment.metadata, input_usd_per_million, output_usd_per_million)
                if assessment.method is RelationMethod.PROVIDER
                else None,
                sent_to_provider=assessment.method is RelationMethod.PROVIDER,
                confidence=assessment.confidence,
                justification=assessment.justification,
            )
        )
    return predictions


async def predict_relation_pairs(
    pairs: list[RelationPairInput] | tuple[RelationPairInput, ...],
    *,
    judge: RelationJudge,
    policy: CandidatePolicy,
    relation_prompt_version: str,
    input_usd_per_million: float | None = None,
    output_usd_per_million: float | None = None,
) -> list[CorrelationPrediction]:
    service = RelationAssessmentService(
        judge=judge,
        repository=_MemoryRelationRepository(),
        relation_prompt_version=relation_prompt_version,
    )
    selector = CandidateSelector(policy)
    predictions: list[CorrelationPrediction] = []
    for pair in pairs:
        decision = selector.select(
            anchor_id=pair.left_id,
            anchor_sheet=pair.left,
            neighbors=[CandidateInput(pair.right_id, pair.semantic_score, pair.right)],
        ).decisions[0]
        if not decision.included:
            predictions.append(
                CorrelationPrediction(
                    str(pair.left_id),
                    str(pair.right_id),
                    False,
                    None,
                    next(
                        (reason for reason in decision.reasons if reason != "candidate_selected"),
                        "unknown",
                    ),
                    None,
                    None,
                )
            )
            continue
        try:
            assessment = await service.assess(
                left_id=pair.left_id,
                right_id=pair.right_id,
                left=pair.left,
                right=pair.right,
            )
        except ProviderError as error:
            predictions.append(
                CorrelationPrediction(
                    str(pair.left_id),
                    str(pair.right_id),
                    True,
                    None,
                    None,
                    error.code.value,
                    _operation(error.metadata, input_usd_per_million, output_usd_per_million),
                    sent_to_provider=True,
                )
            )
            continue
        except ValueError:
            predictions.append(
                CorrelationPrediction(
                    str(pair.left_id),
                    str(pair.right_id),
                    True,
                    None,
                    None,
                    "invalid_relation_semantics",
                    None,
                    sent_to_provider=True,
                )
            )
            continue
        predictions.append(
            CorrelationPrediction(
                str(pair.left_id),
                str(pair.right_id),
                True,
                assessment.relation.value if assessment.relation else None,
                None,
                None,
                _operation(assessment.metadata, input_usd_per_million, output_usd_per_million)
                if assessment.method is RelationMethod.PROVIDER
                else None,
                sent_to_provider=assessment.method is RelationMethod.PROVIDER,
                confidence=assessment.confidence,
                justification=assessment.justification,
            )
        )
    return predictions


def evaluate_predictions(
    predictions: list[CorrelationPrediction],
    *,
    gold_relations: dict[tuple[str, str], str],
) -> CorrelationMetrics:
    canonical_gold = {tuple(sorted(pair)): relation for pair, relation in gold_relations.items()}
    cases = [
        CorrelationCase(
            prediction.left_id,
            prediction.right_id,
            canonical_gold.get(
                tuple(sorted((prediction.left_id, prediction.right_id))),
                "unrelated",
            ),
            prediction.selected,
            prediction.predicted_relation,
            prediction.exclusion_reason,
            prediction.failure_code,
        )
        for prediction in predictions
    ]
    return evaluate_correlation(
        cases,
        theoretical_pairs=len(predictions),
        operational_samples=[item.operation for item in predictions if item.operation],
    )


def _cosine(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    dot = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return round(max(0.0, min(1.0, dot / (left_norm * right_norm))), 6)


def _operation(metadata, input_price, output_price) -> OperationalSample | None:
    if metadata is None:
        return None
    input_units, output_units = metadata.input_units or 0, metadata.output_units or 0
    cost = None
    if input_price is not None and output_price is not None:
        cost = (input_units * input_price + output_units * output_price) / 1_000_000
    return OperationalSample(
        duration_ms=metadata.duration_ms,
        input_units=input_units,
        output_units=output_units,
        cache_hit=metadata.cache_hit,
        estimated_cost_usd=cost,
    )
