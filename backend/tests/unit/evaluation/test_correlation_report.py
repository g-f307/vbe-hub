from vbe_hub.evaluation.correlation_metrics import CorrelationCase, evaluate_correlation
from vbe_hub.evaluation.correlation_protocol import CorrelationExperimentConfig
from vbe_hub.evaluation.correlation_report import build_correlation_report


def config(threshold: float = 0.70, concurrency: int = 1) -> CorrelationExperimentConfig:
    return CorrelationExperimentConfig(
        dataset_version="synthetic-v1",
        dataset_sha256="a" * 64,
        split="evaluation",
        seed=307,
        commit="abc123",
        normalizer_version="1.0.0",
        extraction_model="fake-extractor-v1",
        embedding_model="fake-embedding-v1",
        representation_version="embedding-text-v1",
        relation_model="fake-relation-v1",
        relation_prompt_version="relate-v1",
        max_neighbors=10,
        temporal_window_days=14,
        geographic_level="municipality",
        minimum_semantic_score=threshold,
        minimum_total_score=0.65,
        provider_concurrency=concurrency,
    )


def test_identity_changes_when_threshold_changes() -> None:
    assert config().identity != config(0.75).identity


def test_identity_changes_when_concurrency_changes() -> None:
    assert config(concurrency=1).identity != config(concurrency=4).identity


def test_report_is_deterministic_and_keeps_false_negative_identifiers() -> None:
    cases = [
        CorrelationCase(
            "synthetic-a", "synthetic-b", "updates", False, None, "temporal_gap_exceeded"
        )
    ]
    metrics = evaluate_correlation(cases, theoretical_pairs=4)

    first = build_correlation_report(config=config(), metrics=metrics)
    second = build_correlation_report(config=config(), metrics=metrics)

    assert first == second
    assert first["report_version"] == "correlation-evaluation-report-v1"
    assert first["candidates"]["false_negatives"] == [
        {"left_id": "synthetic-a", "right_id": "synthetic-b", "reason": "temporal_gap_exceeded"}
    ]
