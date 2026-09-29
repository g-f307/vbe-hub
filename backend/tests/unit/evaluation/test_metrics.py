from vbe_hub.evaluation.metrics import EvaluationCase, evaluate_cases


def test_perfect_predictions_produce_perfect_field_metrics() -> None:
    cases = [
        EvaluationCase(
            record_id="record-1",
            gold={"disease_or_condition": "Sarampo", "symptoms": ["febre", "exantema"]},
            prediction={
                "disease_or_condition": "sarampo",
                "symptoms": ["EXANTEMA", "febre"],
            },
        )
    ]

    report = evaluate_cases(
        cases, field_kinds={"disease_or_condition": "scalar", "symptoms": "list"}
    )

    assert report.fields["disease_or_condition"].accuracy == 1.0
    assert report.fields["symptoms"].precision == 1.0
    assert report.fields["symptoms"].recall == 1.0
    assert report.fields["symptoms"].f1 == 1.0


def test_value_when_gold_is_null_is_counted_as_hallucination() -> None:
    report = evaluate_cases(
        [
            EvaluationCase(
                "record-1", {"location.municipality": None}, {"location.municipality": "Manaus"}
            )
        ],
        field_kinds={"location.municipality": "scalar"},
    )

    field = report.fields["location.municipality"]
    assert field.hallucinations == 1
    assert field.hallucination_rate == 1.0
    assert report.errors[0].kind == "hallucination"


def test_hallucinations_do_not_inflate_coverage_above_one() -> None:
    report = evaluate_cases(
        [
            EvaluationCase(
                "record-1", {"disease_or_condition": "sarampo"}, {"disease_or_condition": "sarampo"}
            ),
            EvaluationCase(
                "record-2", {"disease_or_condition": None}, {"disease_or_condition": "dengue"}
            ),
        ],
        field_kinds={"disease_or_condition": "scalar"},
    )

    assert report.fields["disease_or_condition"].coverage == 1.0


def test_null_when_gold_has_value_is_omission_not_correct_null() -> None:
    report = evaluate_cases(
        [
            EvaluationCase(
                "record-1", {"disease_or_condition": "sarampo"}, {"disease_or_condition": None}
            )
        ],
        field_kinds={"disease_or_condition": "scalar"},
    )

    field = report.fields["disease_or_condition"]
    assert field.omissions == 1
    assert field.omission_rate == 1.0
    assert field.correct_nulls == 0
    assert field.coverage == 0.0


def test_lists_ignore_order_and_duplicates_without_inflating_scores() -> None:
    report = evaluate_cases(
        [
            EvaluationCase(
                "record-1",
                {"symptoms": ["febre", "tosse"]},
                {"symptoms": ["tosse", "febre", "febre"]},
            )
        ],
        field_kinds={"symptoms": "list"},
    )

    field = report.fields["symptoms"]
    assert (field.true_positives, field.false_positives, field.false_negatives) == (2, 0, 0)
    assert field.f1 == 1.0


def test_numeric_error_does_not_turn_null_into_zero() -> None:
    report = evaluate_cases(
        [
            EvaluationCase("record-1", {"estimated_cases": None}, {"estimated_cases": None}),
            EvaluationCase("record-2", {"estimated_cases": 10}, {"estimated_cases": 7}),
        ],
        field_kinds={"estimated_cases": "numeric"},
    )

    field = report.fields["estimated_cases"]
    assert field.correct_nulls == 1
    assert field.mean_absolute_error == 3.0
    assert field.numeric_pairs == 1
