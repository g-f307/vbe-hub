from vbe_hub.evaluation.decisions import derive_field_decisions


def test_operational_failure_above_target_blocks_direct_use() -> None:
    decisions = derive_field_decisions(
        fields={
            "disease_or_condition": {
                "hallucination_rate": 0.0,
                "omission_rate": 0.0,
                "f1": None,
            }
        },
        critical_fields=["disease_or_condition"],
        targets={
            "critical_field_hallucination_rate_max": 0.1,
            "critical_field_omission_rate_max": 0.25,
            "symptoms_f1_min": 0.8,
            "operational_failure_rate_max": 0.05,
        },
        operational_failure_rate=0.25,
    )

    assert decisions["disease_or_condition"] == "reduced_weight"
