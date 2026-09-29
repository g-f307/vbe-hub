from __future__ import annotations

import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Literal

FieldKind = Literal["scalar", "list", "numeric"]


@dataclass(frozen=True, slots=True)
class EvaluationCase:
    record_id: str
    gold: Mapping[str, Any]
    prediction: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class EvaluationError:
    record_id: str
    field: str
    kind: str


@dataclass(slots=True)
class FieldMetrics:
    total: int = 0
    gold_present: int = 0
    predicted_present: int = 0
    covered_gold: int = 0
    exact_matches: int = 0
    correct_nulls: int = 0
    hallucinations: int = 0
    omissions: int = 0
    true_positives: int = 0
    false_positives: int = 0
    false_negatives: int = 0
    numeric_pairs: int = 0
    absolute_error_sum: float = 0.0

    @property
    def coverage(self) -> float | None:
        return _ratio(self.covered_gold, self.gold_present)

    @property
    def accuracy(self) -> float | None:
        return _ratio(self.exact_matches + self.correct_nulls, self.total)

    @property
    def hallucination_rate(self) -> float | None:
        gold_nulls = self.total - self.gold_present
        return _ratio(self.hallucinations, gold_nulls)

    @property
    def omission_rate(self) -> float | None:
        return _ratio(self.omissions, self.gold_present)

    @property
    def null_accuracy(self) -> float | None:
        gold_nulls = self.total - self.gold_present
        return _ratio(self.correct_nulls, gold_nulls)

    @property
    def precision(self) -> float | None:
        return _ratio(self.true_positives, self.true_positives + self.false_positives)

    @property
    def recall(self) -> float | None:
        return _ratio(self.true_positives, self.true_positives + self.false_negatives)

    @property
    def f1(self) -> float | None:
        precision = self.precision
        recall = self.recall
        if precision is None or recall is None:
            return None
        if precision + recall == 0:
            return 0.0
        return round(2 * precision * recall / (precision + recall), 6)

    @property
    def mean_absolute_error(self) -> float | None:
        if self.numeric_pairs == 0:
            return None
        return round(self.absolute_error_sum / self.numeric_pairs, 6)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total": self.total,
            "gold_present": self.gold_present,
            "predicted_present": self.predicted_present,
            "coverage": self.coverage,
            "accuracy": self.accuracy,
            "correct_nulls": self.correct_nulls,
            "null_accuracy": self.null_accuracy,
            "hallucinations": self.hallucinations,
            "hallucination_rate": self.hallucination_rate,
            "omissions": self.omissions,
            "omission_rate": self.omission_rate,
            "precision": self.precision,
            "recall": self.recall,
            "f1": self.f1,
            "mean_absolute_error": self.mean_absolute_error,
        }


@dataclass(frozen=True, slots=True)
class EvaluationMetrics:
    fields: Mapping[str, FieldMetrics]
    errors: tuple[EvaluationError, ...] = field(default_factory=tuple)


def evaluate_cases(
    cases: list[EvaluationCase], *, field_kinds: Mapping[str, FieldKind]
) -> EvaluationMetrics:
    fields = {name: FieldMetrics() for name in field_kinds}
    errors: list[EvaluationError] = []
    for case in cases:
        for name, kind in field_kinds.items():
            gold = case.gold.get(name)
            prediction = case.prediction.get(name)
            metrics = fields[name]
            metrics.total += 1
            gold_present = _present(gold, kind)
            prediction_present = _present(prediction, kind)
            metrics.gold_present += int(gold_present)
            metrics.covered_gold += int(gold_present and prediction_present)
            metrics.predicted_present += int(prediction_present)

            if not gold_present and not prediction_present:
                metrics.correct_nulls += 1
                continue
            if not gold_present and prediction_present:
                metrics.hallucinations += 1
                errors.append(EvaluationError(case.record_id, name, "hallucination"))
                continue
            if gold_present and not prediction_present:
                metrics.omissions += 1
                errors.append(EvaluationError(case.record_id, name, "omission"))
                if kind == "list":
                    metrics.false_negatives += len(_normalised_set(gold))
                continue

            if kind == "list":
                expected = _normalised_set(gold)
                actual = _normalised_set(prediction)
                metrics.true_positives += len(expected & actual)
                metrics.false_positives += len(actual - expected)
                metrics.false_negatives += len(expected - actual)
                if expected == actual:
                    metrics.exact_matches += 1
                else:
                    errors.append(EvaluationError(case.record_id, name, "normalization"))
            elif kind == "numeric":
                metrics.numeric_pairs += 1
                metrics.absolute_error_sum += abs(float(gold) - float(prediction))
                if gold == prediction:
                    metrics.exact_matches += 1
                else:
                    errors.append(EvaluationError(case.record_id, name, "normalization"))
            elif _normalise(gold) == _normalise(prediction):
                metrics.exact_matches += 1
            else:
                errors.append(EvaluationError(case.record_id, name, "normalization"))
    return EvaluationMetrics(fields=fields, errors=tuple(errors))


def _present(value: Any, kind: FieldKind) -> bool:
    if value is None:
        return False
    if kind == "list":
        return bool(value)
    return True


def _normalise(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value).strip().casefold())
    return " ".join("".join(char for char in text if not unicodedata.combining(char)).split())


def _normalised_set(value: Any) -> set[str]:
    return {_normalise(item) for item in value}


def _ratio(numerator: int, denominator: int) -> float | None:
    if denominator == 0:
        return None
    return round(numerator / denominator, 6)
