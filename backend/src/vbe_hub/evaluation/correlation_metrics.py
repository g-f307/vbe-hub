from dataclasses import dataclass
from math import ceil

CLASSES = ("duplicate", "corroborates", "updates", "related_context", "unrelated")


@dataclass(frozen=True, slots=True)
class CorrelationCase:
    left_id: str
    right_id: str
    gold_relation: str
    selected: bool
    predicted_relation: str | None
    exclusion_reason: str | None = None
    failure_code: str | None = None


@dataclass(frozen=True, slots=True)
class OperationalSample:
    duration_ms: int
    input_units: int
    output_units: int
    cache_hit: bool
    estimated_cost_usd: float | None


@dataclass(frozen=True, slots=True)
class CandidateMetrics:
    selected_pairs: int
    theoretical_pairs: int
    pair_reduction: float
    precision: float | None
    recall: float | None
    false_negatives: tuple[tuple[str, str, str], ...]


@dataclass(frozen=True, slots=True)
class ClassificationMetrics:
    by_class: dict[str, dict[str, float]]
    confusion: dict[str, dict[str, int]]
    macro_f1: float
    micro_f1: float
    failures: int


@dataclass(frozen=True, slots=True)
class OperationalMetrics:
    provider_calls: int
    cache_hits: int
    latency_ms_p50: int | None
    latency_ms_p95: int | None
    input_units: int
    output_units: int
    estimated_cost_usd: float | None


@dataclass(frozen=True, slots=True)
class CorrelationMetrics:
    candidates: CandidateMetrics
    classification: ClassificationMetrics
    operations: OperationalMetrics


def evaluate_correlation(
    cases: list[CorrelationCase],
    *,
    theoretical_pairs: int,
    operational_samples: list[OperationalSample] | None = None,
) -> CorrelationMetrics:
    if theoretical_pairs < 0:
        raise ValueError("theoretical_pairs must be non-negative")
    positives = [case for case in cases if case.gold_relation != "unrelated"]
    selected = [case for case in cases if case.selected]
    selected_positive = [case for case in selected if case.gold_relation != "unrelated"]
    missed = tuple(
        sorted(
            (case.left_id, case.right_id, case.exclusion_reason or "unknown")
            for case in positives
            if not case.selected
        )
    )
    candidate_metrics = CandidateMetrics(
        selected_pairs=len(selected),
        theoretical_pairs=theoretical_pairs,
        pair_reduction=_ratio(theoretical_pairs - len(selected), theoretical_pairs) or 0.0,
        precision=_ratio(len(selected_positive), len(selected)),
        recall=_ratio(len(selected_positive), len(positives)),
        false_negatives=missed,
    )
    confusion = {gold: {predicted: 0 for predicted in CLASSES} for gold in CLASSES}
    failures = 0
    for case in cases:
        if case.failure_code:
            failures += 1
            continue
        prediction = case.predicted_relation if case.selected else "unrelated"
        if case.gold_relation not in CLASSES or prediction not in CLASSES:
            raise ValueError("relations must use the versioned enum")
        confusion[case.gold_relation][prediction] += 1
    by_class = {}
    total_tp = total_fp = total_fn = 0
    for relation in CLASSES:
        tp = confusion[relation][relation]
        fp = sum(confusion[gold][relation] for gold in CLASSES if gold != relation)
        fn = sum(confusion[relation][pred] for pred in CLASSES if pred != relation)
        precision, recall = _ratio(tp, tp + fp) or 0.0, _ratio(tp, tp + fn) or 0.0
        f1 = (
            0.0
            if precision + recall == 0
            else round(2 * precision * recall / (precision + recall), 6)
        )
        by_class[relation] = {"precision": precision, "recall": recall, "f1": f1}
        total_tp += tp
        total_fp += fp
        total_fn += fn
    micro_p = _ratio(total_tp, total_tp + total_fp) or 0.0
    micro_r = _ratio(total_tp, total_tp + total_fn) or 0.0
    micro_f1 = (
        0.0 if micro_p + micro_r == 0 else round(2 * micro_p * micro_r / (micro_p + micro_r), 6)
    )
    classification = ClassificationMetrics(
        by_class=by_class,
        confusion=confusion,
        macro_f1=round(sum(item["f1"] for item in by_class.values()) / len(CLASSES), 6),
        micro_f1=micro_f1,
        failures=failures,
    )
    samples = operational_samples or []
    paid = [sample for sample in samples if not sample.cache_hit]
    durations = sorted(sample.duration_ms for sample in samples)
    operations = OperationalMetrics(
        provider_calls=len(paid),
        cache_hits=len(samples) - len(paid),
        latency_ms_p50=_percentile(durations, 0.5),
        latency_ms_p95=_percentile(durations, 0.95),
        input_units=sum(sample.input_units for sample in paid),
        output_units=sum(sample.output_units for sample in paid),
        estimated_cost_usd=_total_cost(paid),
    )
    return CorrelationMetrics(candidate_metrics, classification, operations)


def _ratio(numerator: int, denominator: int) -> float | None:
    return None if denominator == 0 else round(numerator / denominator, 6)


def _percentile(values: list[int], percentile: float) -> int | None:
    return None if not values else values[max(0, ceil(len(values) * percentile) - 1)]


def _total_cost(samples: list[OperationalSample]) -> float | None:
    if not samples:
        return 0.0
    if any(sample.estimated_cost_usd is None for sample in samples):
        return None
    return round(sum(sample.estimated_cost_usd or 0.0 for sample in samples), 8)
