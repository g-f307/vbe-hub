from vbe_hub.evaluation.metrics import EvaluationCase
from vbe_hub.evaluation.report import build_report


def test_report_is_deterministic_and_lists_errors_by_synthetic_identifier() -> None:
    kwargs = {
        "experiment": {"identity": "abc123", "provider": "test"},
        "cases": [
            EvaluationCase(
                "synthetic-2",
                {"disease_or_condition": None},
                {"disease_or_condition": "dengue"},
            )
        ],
        "field_kinds": {"disease_or_condition": "scalar"},
        "execution": {"attempted": 1, "succeeded": 1, "failed": 0},
    }

    first = build_report(**kwargs)
    second = build_report(**kwargs)

    assert first == second
    assert first["fields"]["disease_or_condition"]["hallucinations"] == 1
    assert first["errors"] == [
        {"record_id": "synthetic-2", "field": "disease_or_condition", "kind": "hallucination"}
    ]
