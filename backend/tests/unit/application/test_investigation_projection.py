from uuid import UUID

from vbe_hub.application.investigations.projection import compose_technical_sheet


def test_evidence_complements_missing_fields_and_preserves_head_values() -> None:
    head = UUID(int=1)
    evidence = UUID(int=2)

    projection = compose_technical_sheet(
        head,
        {"symptoms": ["febre"], "location": {"district": "Zumbi"}},
        [
            (
                evidence,
                {
                    "symptoms": ["febre", "rigidez de nuca"],
                    "location": {"city": "Manaus", "district": "Centro"},
                },
            )
        ],
    )

    assert projection.technical_sheet == {
        "symptoms": ["febre", "rigidez de nuca"],
        "location": {"district": "Zumbi", "city": "Manaus"},
    }
    assert projection.provenance["symptoms"] == [str(head), str(evidence)]
    assert projection.provenance["location.city"] == [str(evidence)]
    assert projection.conflicts == [
        {
            "field": "location.district",
            "kept_value": "Zumbi",
            "alternative_value": "Centro",
            "source_signal_id": str(evidence),
        }
    ]


def test_empty_evidence_sheet_does_not_change_projection() -> None:
    head = UUID(int=1)

    projection = compose_technical_sheet(head, {"syndrome": "febril"}, [(UUID(int=2), None)])

    assert projection.technical_sheet == {"syndrome": "febril"}
    assert projection.provenance == {"syndrome": [str(head)]}
    assert projection.conflicts == []
