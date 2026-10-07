from vbe_hub.evaluation.grouping_metrics import (
    EvaluatedCluster,
    FailureStage,
    GroupingEvaluationInput,
    evaluate_grouping,
)


def test_perfect_clusters_produce_perfect_metrics() -> None:
    result = evaluate_grouping(
        GroupingEvaluationInput(
            gold_event_by_record={"a": "event-1", "b": "event-1", "c": "event-2"},
            clusters=(
                EvaluatedCluster("signal-1", ("a", "b")),
                EvaluatedCluster("signal-2", ("c",)),
            ),
        )
    )

    assert result.pairwise.precision == 1.0
    assert result.pairwise.recall == 1.0
    assert result.pairwise.f1 == 1.0
    assert result.b_cubed.precision == 1.0
    assert result.b_cubed.recall == 1.0
    assert result.b_cubed.f1 == 1.0
    assert result.purity == 1.0
    assert result.inverse_purity == 1.0
    assert result.merges == ()
    assert result.splits == ()


def test_merged_events_reduce_precision_and_identify_members() -> None:
    result = evaluate_grouping(
        GroupingEvaluationInput(
            gold_event_by_record={"a": "event-1", "b": "event-1", "c": "event-2"},
            clusters=(EvaluatedCluster("signal-1", ("a", "b", "c")),),
        )
    )

    assert result.pairwise.precision == 0.333333
    assert result.pairwise.recall == 1.0
    assert result.purity == 0.666667
    assert result.merges[0].cluster_id == "signal-1"
    assert result.merges[0].gold_event_ids == ("event-1", "event-2")
    assert result.merges[0].record_ids == ("a", "b", "c")


def test_fragmented_event_reduces_recall_and_identifies_clusters() -> None:
    result = evaluate_grouping(
        GroupingEvaluationInput(
            gold_event_by_record={"a": "event-1", "b": "event-1", "c": "event-1"},
            clusters=(
                EvaluatedCluster("signal-1", ("a", "b")),
                EvaluatedCluster("signal-2", ("c",)),
            ),
        )
    )

    assert result.pairwise.precision == 1.0
    assert result.pairwise.recall == 0.333333
    assert result.inverse_purity == 0.666667
    assert result.splits[0].gold_event_id == "event-1"
    assert result.splits[0].cluster_ids == ("signal-1", "signal-2")


def test_missing_record_is_attributed_to_first_failed_pipeline_stage() -> None:
    result = evaluate_grouping(
        GroupingEvaluationInput(
            gold_event_by_record={"a": "event-1", "b": "event-1"},
            clusters=(EvaluatedCluster("signal-1", ("a",)),),
            first_failure_by_record={"b": FailureStage.CANDIDATES},
        )
    )

    assert result.lost_record_ids == ("b",)
    assert result.failure_counts == {"candidates": 1}
    assert result.splits[0].missing_record_ids == ("b",)


def test_context_record_does_not_create_false_merge() -> None:
    result = evaluate_grouping(
        GroupingEvaluationInput(
            gold_event_by_record={"a": "event-1", "b": "event-2"},
            clusters=(
                EvaluatedCluster("signal-1", ("a",), context_record_ids=("b",)),
                EvaluatedCluster("signal-2", ("b",)),
            ),
        )
    )

    assert result.pairwise.precision == 1.0
    assert result.merges == ()


def test_duplicate_core_membership_is_rejected() -> None:
    evaluation = GroupingEvaluationInput(
        gold_event_by_record={"a": "event-1"},
        clusters=(
            EvaluatedCluster("signal-1", ("a",)),
            EvaluatedCluster("signal-2", ("a",)),
        ),
    )

    try:
        evaluate_grouping(evaluation)
    except ValueError as error:
        assert str(error) == "record a belongs to multiple core clusters"
    else:
        raise AssertionError("duplicate core membership was accepted")
