from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from itertools import combinations


class FailureStage(StrEnum):
    EXTRACTION = "extraction"
    CANDIDATES = "candidates"
    RELATION = "relation"
    GROUPING = "grouping"
    REVIEW = "review"


@dataclass(frozen=True, slots=True)
class EvaluatedCluster:
    cluster_id: str
    core_record_ids: tuple[str, ...]
    context_record_ids: tuple[str, ...] = ()
    relation_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class GroupingEvaluationInput:
    gold_event_by_record: Mapping[str, str]
    clusters: tuple[EvaluatedCluster, ...]
    first_failure_by_record: Mapping[str, FailureStage] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class PrecisionRecallF1:
    precision: float
    recall: float
    f1: float


@dataclass(frozen=True, slots=True)
class MergeError:
    cluster_id: str
    gold_event_ids: tuple[str, ...]
    record_ids: tuple[str, ...]
    relation_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SplitError:
    gold_event_id: str
    cluster_ids: tuple[str, ...]
    missing_record_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class GroupingMetrics:
    pairwise: PrecisionRecallF1
    b_cubed: PrecisionRecallF1
    purity: float
    inverse_purity: float
    merges: tuple[MergeError, ...]
    splits: tuple[SplitError, ...]
    lost_record_ids: tuple[str, ...]
    spurious_record_ids: tuple[str, ...]
    spurious_cluster_ids: tuple[str, ...]
    failure_counts: Mapping[str, int]
    cluster_size_distribution: Mapping[int, int]


def evaluate_grouping(evaluation: GroupingEvaluationInput) -> GroupingMetrics:
    predicted_by_record: dict[str, str] = {}
    cluster_by_id: dict[str, EvaluatedCluster] = {}
    for cluster in evaluation.clusters:
        if cluster.cluster_id in cluster_by_id:
            raise ValueError(f"cluster id {cluster.cluster_id} is duplicated")
        cluster_by_id[cluster.cluster_id] = cluster
        for record_id in cluster.core_record_ids:
            if record_id in predicted_by_record:
                raise ValueError(f"record {record_id} belongs to multiple core clusters")
            predicted_by_record[record_id] = cluster.cluster_id

    gold = dict(evaluation.gold_event_by_record)
    record_ids = tuple(sorted(gold))
    pairwise = _pairwise(record_ids, gold, predicted_by_record)
    b_cubed = _b_cubed(record_ids, gold, predicted_by_record)
    merges = _merges(evaluation.clusters, gold)
    splits = _splits(gold, predicted_by_record)
    lost = tuple(record_id for record_id in record_ids if record_id not in predicted_by_record)
    spurious = tuple(sorted(set(predicted_by_record) - set(gold)))
    spurious_clusters = tuple(
        sorted(
            cluster.cluster_id
            for cluster in evaluation.clusters
            if cluster.core_record_ids
            and not set(cluster.core_record_ids).intersection(gold)
        )
    )
    failures = Counter(
        evaluation.first_failure_by_record[record_id].value
        for record_id in lost
        if record_id in evaluation.first_failure_by_record
    )
    return GroupingMetrics(
        pairwise=pairwise,
        b_cubed=b_cubed,
        purity=_purity(evaluation.clusters, gold),
        inverse_purity=_inverse_purity(gold, predicted_by_record),
        merges=merges,
        splits=splits,
        lost_record_ids=lost,
        spurious_record_ids=spurious,
        spurious_cluster_ids=spurious_clusters,
        failure_counts=dict(sorted(failures.items())),
        cluster_size_distribution=dict(
            sorted(Counter(len(item.core_record_ids) for item in evaluation.clusters).items())
        ),
    )


def _pairwise(
    record_ids: tuple[str, ...],
    gold: Mapping[str, str],
    predicted: Mapping[str, str],
) -> PrecisionRecallF1:
    true_positive = false_positive = false_negative = 0
    for left, right in combinations(record_ids, 2):
        same_gold = gold[left] == gold[right]
        same_prediction = (
            left in predicted
            and right in predicted
            and predicted[left] == predicted[right]
        )
        true_positive += int(same_gold and same_prediction)
        false_positive += int(not same_gold and same_prediction)
        false_negative += int(same_gold and not same_prediction)
    return _scores(true_positive, false_positive, false_negative)


def _b_cubed(
    record_ids: tuple[str, ...],
    gold: Mapping[str, str],
    predicted: Mapping[str, str],
) -> PrecisionRecallF1:
    if not record_ids:
        return PrecisionRecallF1(1.0, 1.0, 1.0)
    gold_members = _members_by_value(gold)
    predicted_members = _members_by_value(predicted)
    precision_values: list[float] = []
    recall_values: list[float] = []
    for record_id in record_ids:
        cluster_id = predicted.get(record_id)
        if cluster_id is None:
            precision_values.append(0.0)
            recall_values.append(0.0)
            continue
        overlap = len(
            gold_members[gold[record_id]].intersection(predicted_members[cluster_id])
        )
        precision_values.append(overlap / len(predicted_members[cluster_id]))
        recall_values.append(overlap / len(gold_members[gold[record_id]]))
    precision = sum(precision_values) / len(record_ids)
    recall = sum(recall_values) / len(record_ids)
    return PrecisionRecallF1(_round(precision), _round(recall), _f1(precision, recall))


def _purity(clusters: tuple[EvaluatedCluster, ...], gold: Mapping[str, str]) -> float:
    assigned = 0
    majority = 0
    for cluster in clusters:
        counts = Counter(gold[item] for item in cluster.core_record_ids if item in gold)
        assigned += sum(counts.values())
        majority += max(counts.values(), default=0)
    return _round(majority / assigned) if assigned else (1.0 if not gold else 0.0)


def _inverse_purity(gold: Mapping[str, str], predicted: Mapping[str, str]) -> float:
    if not gold:
        return 1.0
    predicted_by_event: dict[str, Counter[str]] = defaultdict(Counter)
    for record_id, event_id in gold.items():
        if record_id in predicted:
            predicted_by_event[event_id][predicted[record_id]] += 1
    covered = sum(max(counts.values(), default=0) for counts in predicted_by_event.values())
    return _round(covered / len(gold))


def _merges(
    clusters: tuple[EvaluatedCluster, ...], gold: Mapping[str, str]
) -> tuple[MergeError, ...]:
    errors = []
    for cluster in clusters:
        records = tuple(sorted(item for item in cluster.core_record_ids if item in gold))
        event_ids = tuple(sorted({gold[item] for item in records}))
        if len(event_ids) > 1:
            errors.append(
                MergeError(
                    cluster_id=cluster.cluster_id,
                    gold_event_ids=event_ids,
                    record_ids=records,
                    relation_ids=tuple(sorted(cluster.relation_ids)),
                )
            )
    return tuple(sorted(errors, key=lambda item: item.cluster_id))


def _splits(
    gold: Mapping[str, str], predicted: Mapping[str, str]
) -> tuple[SplitError, ...]:
    records_by_event = _members_by_value(gold)
    errors = []
    for event_id, records in sorted(records_by_event.items()):
        cluster_ids = tuple(sorted({predicted[item] for item in records if item in predicted}))
        missing = tuple(sorted(item for item in records if item not in predicted))
        if len(cluster_ids) + int(bool(missing)) > 1 or (missing and not cluster_ids):
            errors.append(SplitError(event_id, cluster_ids, missing))
    return tuple(errors)


def _members_by_value(values: Mapping[str, str]) -> dict[str, set[str]]:
    result: dict[str, set[str]] = defaultdict(set)
    for key, value in values.items():
        result[value].add(key)
    return result


def _scores(true_positive: int, false_positive: int, false_negative: int) -> PrecisionRecallF1:
    precision = true_positive / (true_positive + false_positive) if false_positive else 1.0
    recall = true_positive / (true_positive + false_negative) if false_negative else 1.0
    return PrecisionRecallF1(_round(precision), _round(recall), _f1(precision, recall))


def _f1(precision: float, recall: float) -> float:
    return _round(2 * precision * recall / (precision + recall)) if precision + recall else 0.0


def _round(value: float) -> float:
    return round(value, 6)
