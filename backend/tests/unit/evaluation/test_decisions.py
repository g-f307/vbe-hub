from vbe_hub.evaluation.decisions import derive_field_decisions


def test_critical_fields_are_not_used_directly_when_targets_fail() -> None:
    decisions = derive_field_decisions(
        fields={
            "disease_or_condition": {"hallucination_rate": 0.5, "omission_rate": 0.0, "f1": None},
            "location.municipality": {"hallucination_rate": 0.0, "omission_rate": 0.2, "f1": None},
            "symptoms": {"hallucination_rate": None, "omission_rate": 0.0, "f1": 0.7},
        },
        critical_fields=["disease_or_condition", "location.municipality"],
        targets={
            "critical_field_hallucination_rate_max": 0.1,
            "critical_field_omission_rate_max": 0.25,
            "symptoms_f1_min": 0.8,
        },
    )

    assert decisions["disease_or_condition"] == "evidence_only"
    assert decisions["location.municipality"] == "direct"
    assert decisions["symptoms"] == "reduced_weight"
