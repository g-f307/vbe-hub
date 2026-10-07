import json
from collections import Counter

from vbe_hub.evaluation.grouping_dataset import build_grouping_dataset
from vbe_hub.evaluation.grouping_experiment import run_grouping_experiment


def test_grouping_splits_are_disjoint_and_gold_is_physically_separate() -> None:
    calibration = build_grouping_dataset(split="calibration", event_count=20, seed=4170)
    evaluation = build_grouping_dataset(split="evaluation", event_count=60, seed=5170)

    calibration_ids = {str(item.record_id) for item in calibration.inputs.records}
    evaluation_ids = {str(item.record_id) for item in evaluation.inputs.records}
    serialized_inputs = json.dumps(calibration.inputs.to_dict(), sort_keys=True)
    relation_counts = Counter(
        item.relation.value
        for item in evaluation.inputs.reviewed_relations
        if item.relation is not None and item.relation.value != "related_context"
    )

    assert calibration_ids.isdisjoint(evaluation_ids)
    assert "gold_event" not in serialized_inputs
    assert len(evaluation.gold.event_by_record) >= 240
    assert relation_counts["duplicate"] >= 50
    assert relation_counts["corroborates"] >= 50
    assert relation_counts["updates"] >= 50
    assert set(evaluation.inputs.scenario_counts) == {
        "complete",
        "conflicting_bridge",
        "missing_condition",
        "missing_location",
        "partial_date",
        "weak_context_bridge",
    }


def test_grouping_experiment_evaluates_automatic_and_reviewed_results_separately() -> None:
    report = run_grouping_experiment(
        split="evaluation",
        event_count=60,
        seed=5170,
        commit="abc1234",
        bootstrap_iterations=100,
    )

    assert report["report_version"] == "grouping-experiment-report-v1"
    assert report["dataset"]["events"] == 60
    assert report["automatic"]["merges"]["count"] == 1
    assert report["reviewed"]["merges"]["count"] == 0
    assert report["reviewed"]["pairwise"]["f1"] == 1.0
    assert report["review"]["decisions"] == 1
    assert report["review"]["actions"] == {"reject": 1}
    assert report["decision"]["status"] == "approve_with_caveats"
    assert report["operations"] == {
        "provider_calls": 0,
        "cache_hits": 0,
        "failures": 0,
        "latency_ms": {"p50": 0, "p95": 0},
        "input_units": 0,
        "output_units": 0,
        "estimated_cost_usd": 0.0,
    }


def test_grouping_experiment_is_reproducible_and_identity_tracks_configuration() -> None:
    first = run_grouping_experiment(
        split="evaluation",
        event_count=60,
        seed=5170,
        commit="abc1234",
        bootstrap_iterations=20,
    )
    repeated = run_grouping_experiment(
        split="evaluation",
        event_count=60,
        seed=5170,
        commit="abc1234",
        bootstrap_iterations=20,
    )
    changed = run_grouping_experiment(
        split="evaluation",
        event_count=60,
        seed=5171,
        commit="abc1234",
        bootstrap_iterations=20,
    )

    assert repeated == first
    assert changed["experiment"]["identity"] != first["experiment"]["identity"]
