from dataclasses import asdict
from typing import Any

from vbe_hub.evaluation.correlation_metrics import CorrelationMetrics
from vbe_hub.evaluation.correlation_protocol import CorrelationExperimentConfig


def build_correlation_report(
    *, config: CorrelationExperimentConfig, metrics: CorrelationMetrics
) -> dict[str, Any]:
    candidates = asdict(metrics.candidates)
    candidates["false_negatives"] = [
        {"left_id": left, "right_id": right, "reason": reason}
        for left, right, reason in metrics.candidates.false_negatives
    ]
    return {
        "report_version": "correlation-evaluation-report-v1",
        "experiment": {**config.model_dump(), "identity": config.identity},
        "candidates": candidates,
        "classification": asdict(metrics.classification),
        "operations": asdict(metrics.operations),
    }
