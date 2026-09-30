from vbe_hub.evaluation.correlation_metrics import (
    CorrelationCase,
    OperationalSample,
    evaluate_correlation,
)


def test_perfect_funel_reports_literal_metrics_for_every_class() -> None:
    cases = [
        CorrelationCase("a", "b", "duplicate", True, "duplicate"),
        CorrelationCase("a", "c", "corroborates", True, "corroborates"),
        CorrelationCase("a", "d", "updates", True, "updates"),
        CorrelationCase("a", "e", "related_context", True, "related_context"),
        CorrelationCase("a", "f", "unrelated", False, None, "semantic_score_below_minimum"),
    ]

    report = evaluate_correlation(cases, theoretical_pairs=10)

    assert report.candidates.recall == 1.0
    assert report.candidates.precision == 1.0
    assert report.candidates.pair_reduction == 0.6
    assert report.classification.macro_f1 == 1.0
    assert report.classification.confusion["unrelated"]["unrelated"] == 1


def test_missed_positive_reduces_candidate_recall_even_with_perfect_received_predictions() -> None:
    cases = [
        CorrelationCase("a", "b", "corroborates", False, None, "temporal_gap_exceeded"),
        CorrelationCase("a", "c", "duplicate", True, "duplicate"),
    ]

    report = evaluate_correlation(cases, theoretical_pairs=6)

    assert report.candidates.recall == 0.5
    assert report.classification.macro_f1 < 1
    assert report.candidates.false_negatives == (("a", "b", "temporal_gap_exceeded"),)


def test_failure_is_not_silently_counted_as_unrelated() -> None:
    report = evaluate_correlation(
        [CorrelationCase("a", "b", "unrelated", True, None, failure_code="timeout")],
        theoretical_pairs=1,
    )

    assert report.classification.failures == 1
    assert report.classification.failures_by_code == {"timeout": 1}
    assert report.classification.confusion["unrelated"]["unrelated"] == 0


def test_operational_metrics_exclude_cache_hits_from_calls_and_cost() -> None:
    samples = [
        OperationalSample(10, 100, 20, False, 0.01),
        OperationalSample(30, 100, 20, True, 0.01),
        OperationalSample(20, 50, 10, False, 0.005),
    ]

    report = evaluate_correlation([], theoretical_pairs=0, operational_samples=samples)

    assert report.operations.provider_calls == 2
    assert report.operations.cache_hits == 1
    assert report.operations.latency_ms_p50 == 20
    assert report.operations.latency_ms_p95 == 30
    assert report.operations.estimated_cost_usd == 0.015


def test_operational_metrics_keep_unknown_cost_unavailable() -> None:
    report = evaluate_correlation(
        [],
        theoretical_pairs=0,
        operational_samples=[OperationalSample(10, 100, 20, False, None)],
    )

    assert report.operations.provider_calls == 1
    assert report.operations.estimated_cost_usd is None
