from datetime import date
from uuid import UUID

from vbe_hub.application.ai import RelationKind
from vbe_hub.application.correlation.signals import (
    ConsolidationPolicy,
    SignalConsolidationService,
    SignalRecord,
    SignalRelationInput,
)


def uid(value: int) -> UUID:
    return UUID(int=value)


def sheet(
    *,
    municipality: str | None = "Manaus",
    condition: str | None = "Sarampo",
    syndrome: str | None = "Síndrome febril exantemática",
    symptoms: tuple[str, ...] = ("febre", "manchas vermelhas"),
    start: str | None = "2026-01-01",
    end: str | None = None,
    cases: int | None = 3,
) -> dict:
    return {
        "disease_or_condition": condition,
        "syndrome": syndrome,
        "symptoms": list(symptoms),
        "estimated_cases": cases,
        "estimated_deaths": None,
        "temporal": {"start": start, "end": end, "precision": "day"},
        "location": {
            "country": "Brasil",
            "state": "Amazonas",
            "municipality": municipality,
            "district": None,
            "specific": None,
            "precision": "municipality",
        },
    }


def record(value: int, **changes) -> SignalRecord:
    return SignalRecord(record_id=uid(value), technical_sheet=sheet(**changes))


def relation(
    value: int,
    left: int,
    right: int,
    kind: RelationKind | None,
    *,
    updating: int | None = None,
    succeeded: bool = True,
) -> SignalRelationInput:
    return SignalRelationInput(
        assessment_id=uid(value),
        left_id=uid(left),
        right_id=uid(right),
        relation=kind,
        updating_record_id=uid(updating) if updating else None,
        succeeded=succeeded,
    )


def service(version: str = "signal-policy-v1") -> SignalConsolidationService:
    return SignalConsolidationService(ConsolidationPolicy(version=version))


def test_duplicates_and_corroboration_form_one_auditable_signal() -> None:
    result = service().consolidate(
        records=[record(1), record(2), record(3, cases=4)],
        relations=[
            relation(101, 1, 2, RelationKind.DUPLICATE),
            relation(102, 2, 3, RelationKind.CORROBORATES),
        ],
    )

    assert len(result.signals) == 1
    signal = result.signals[0]
    assert signal.core_record_ids == (uid(1), uid(2), uid(3))
    assert signal.context_record_ids == ()
    assert signal.relation_ids == (uid(101), uid(102))
    assert signal.policy_version == "signal-policy-v1"
    assert signal.field_provenance["disease_or_condition"][0].record_ids == (
        uid(1),
        uid(2),
        uid(3),
    )
    assert signal.title == "Sinal sugerido: Sarampo em Manaus"


def test_update_extends_period_and_preserves_magnitude_history() -> None:
    result = service().consolidate(
        records=[
            record(1, start="2026-01-01", cases=3),
            record(2, start="2026-01-03", end="2026-01-04", cases=12),
        ],
        relations=[relation(101, 1, 2, RelationKind.UPDATES, updating=2)],
    )

    signal = result.signals[0]
    assert signal.period_start == date(2026, 1, 1)
    assert signal.period_end == date(2026, 1, 4)
    assert [(item.record_id, item.estimated_cases) for item in signal.magnitude_history] == [
        (uid(1), 3),
        (uid(2), 12),
    ]
    assert signal.current_estimated_cases == 12
    assert "magnitude_values_differ" in signal.divergence_codes


def test_related_context_attaches_without_becoming_a_core_member() -> None:
    result = service().consolidate(
        records=[
            record(1),
            record(2, cases=4),
            record(3, condition="Sarampo", syndrome=None, symptoms=(), cases=None),
        ],
        relations=[
            relation(101, 1, 2, RelationKind.CORROBORATES),
            relation(102, 2, 3, RelationKind.RELATED_CONTEXT),
        ],
    )

    assert len(result.signals) == 1
    signal = result.signals[0]
    assert signal.core_record_ids == (uid(1), uid(2))
    assert signal.context_record_ids == (uid(3),)
    assert signal.relation_ids == (uid(101), uid(102))


def test_weak_bridge_does_not_join_two_established_events() -> None:
    result = service().consolidate(
        records=[
            record(1, municipality="Manaus"),
            record(2, municipality="Manaus"),
            record(3, municipality="Parintins"),
            record(4, municipality="Parintins"),
        ],
        relations=[
            relation(101, 1, 2, RelationKind.CORROBORATES),
            relation(102, 3, 4, RelationKind.CORROBORATES),
            relation(103, 2, 3, RelationKind.RELATED_CONTEXT),
        ],
    )

    assert [item.core_record_ids for item in result.signals] == [
        (uid(1), uid(2)),
        (uid(3), uid(4)),
    ]
    assert result.conflicts[0].code == "weak_bridge_blocked"
    assert result.conflicts[0].relation_id == uid(103)


def test_transitive_merge_is_blocked_by_strong_geographic_conflict() -> None:
    result = service().consolidate(
        records=[
            record(1, municipality="Manaus"),
            record(2, municipality=None),
            record(3, municipality="Parintins"),
        ],
        relations=[
            relation(101, 1, 2, RelationKind.CORROBORATES),
            relation(102, 2, 3, RelationKind.CORROBORATES),
        ],
    )

    assert [item.core_record_ids for item in result.signals] == [
        (uid(1), uid(2)),
        (uid(3),),
    ]
    assert result.conflicts[0].code == "geographic_conflict"
    assert result.conflicts[0].relation_id == uid(102)


def test_failed_relation_does_not_group_records() -> None:
    result = service().consolidate(
        records=[record(1), record(2)],
        relations=[relation(101, 1, 2, None, succeeded=False)],
    )

    assert [item.core_record_ids for item in result.signals] == [(uid(1),), (uid(2),)]
    assert all(not item.relation_ids for item in result.signals)


def test_same_policy_and_origins_produce_same_identity_but_new_policy_versions_history() -> None:
    records = [record(1), record(2)]
    relations = [relation(101, 1, 2, RelationKind.CORROBORATES)]

    first = service("signal-policy-v1").consolidate(records=records, relations=relations)
    repeated = service("signal-policy-v1").consolidate(records=records, relations=relations)
    revised = service("signal-policy-v2").consolidate(records=records, relations=relations)

    assert first.signals[0].id == repeated.signals[0].id
    assert first.signals[0].identity_key == repeated.signals[0].identity_key
    assert revised.signals[0].id != first.signals[0].id
    assert revised.signals[0].identity_key != first.signals[0].identity_key
