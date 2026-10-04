from datetime import UTC, date, datetime
from uuid import UUID

from vbe_hub.application.ai import RelationKind
from vbe_hub.application.correlation.priority import (
    PriorityCalculator,
    PriorityPolicy,
    PriorityRecord,
    PriorityRelation,
    PriorityWeights,
    TriageBand,
)
from vbe_hub.application.correlation.signals import (
    ConsolidatedSignal,
    FieldValue,
    MagnitudeObservation,
)
from vbe_hub.domain.records import SourceKind

EVALUATED_AT = datetime(2026, 10, 3, 12, 0, tzinfo=UTC)


def uid(value: int) -> UUID:
    return UUID(int=value)


def signal(
    *,
    record_ids: tuple[int, ...] = (1,),
    period_end: date | None = date(2026, 10, 2),
    cases: int | None = 10,
    deaths: int | None = None,
    symptoms: tuple[str, ...] = ("febre",),
    divergences: tuple[str, ...] = (),
) -> ConsolidatedSignal:
    ids = tuple(uid(item) for item in record_ids)
    observations = (
        (
            MagnitudeObservation(
                record_id=ids[0],
                observed_at=period_end,
                estimated_cases=cases,
                estimated_deaths=deaths,
            ),
        )
        if cases is not None or deaths is not None
        else ()
    )
    return ConsolidatedSignal(
        id=uid(900),
        identity_key="a" * 64,
        policy_version="signal-policy-v1",
        processing_state="suggested",
        title="Sinal sintético",
        summary="Evidência sintética para teste.",
        core_record_ids=ids,
        context_record_ids=(),
        relation_ids=(),
        relation_roles={},
        period_start=period_end,
        period_end=period_end,
        location={
            "country": "Brasil",
            "state": "Amazonas",
            "municipality": "Manaus",
            "district": None,
        },
        conditions=("Sarampo",),
        symptoms=symptoms,
        magnitude_history=observations,
        current_estimated_cases=cases,
        field_provenance={
            "disease_or_condition": (FieldValue("Sarampo", ids),),
        },
        divergence_codes=divergences,
    )


def record(
    value: int,
    *,
    source_name: str = "fonte-a",
    precision: str | None = "municipality",
    cases: int | None = 10,
    deaths: int | None = None,
    symptoms: tuple[str, ...] = ("febre",),
) -> PriorityRecord:
    return PriorityRecord(
        record_id=uid(value),
        source_kind=SourceKind.MEDIA,
        source_name=source_name,
        technical_sheet={
            "disease_or_condition": "Sarampo",
            "symptoms": list(symptoms),
            "estimated_cases": cases,
            "estimated_deaths": deaths,
            "temporal": {"start": "2026-10-02", "end": None, "precision": "day"},
            "location": {
                "country": "Brasil",
                "state": "Amazonas",
                "municipality": "Manaus",
                "district": None,
                "precision": precision,
            },
        },
    )


def calculate(
    item: ConsolidatedSignal,
    records: list[PriorityRecord],
    relations: list[PriorityRelation] | None = None,
    policy: PriorityPolicy | None = None,
):
    return PriorityCalculator(policy or PriorityPolicy.v1()).calculate(
        signal=item,
        records=records,
        relations=relations or [],
        evaluated_at=EVALUATED_AT,
    )


def test_independent_sources_raise_priority_without_counting_duplicate_vehicle() -> None:
    item = signal(record_ids=(1, 2))
    duplicate = calculate(
        item,
        [record(1), record(2, source_name="fonte-a")],
        [PriorityRelation(uid(101), RelationKind.DUPLICATE, (uid(1), uid(2)))],
    )
    corroborated = calculate(
        item,
        [record(1), record(2, source_name="fonte-b")],
        [PriorityRelation(uid(102), RelationKind.CORROBORATES, (uid(1), uid(2)))],
    )

    assert duplicate.components["corroboration"].value == 0
    assert duplicate.components["corroboration"].facts["independent_sources"] == 1
    assert corroborated.components["corroboration"].value == 0.7
    assert corroborated.score > duplicate.score
    assert corroborated.components["corroboration"].origin_ids == (uid(1), uid(2))


def test_old_signal_loses_recency_without_erasing_explicit_severity() -> None:
    recent = calculate(
        signal(period_end=date(2026, 10, 2), deaths=1),
        [record(1, deaths=1)],
    )
    old = calculate(
        signal(period_end=date(2026, 7, 1), deaths=1),
        [record(1, deaths=1)],
    )

    assert recent.components["recency"].value > old.components["recency"].value
    assert old.components["recency"].value == 0
    assert recent.components["severity"].value == old.components["severity"].value == 1


def test_unknown_magnitude_and_deaths_remain_unknown_and_create_explicit_gaps() -> None:
    result = calculate(
        signal(cases=None, deaths=None),
        [record(1, cases=None, deaths=None)],
    )

    assert result.components["magnitude"].value is None
    assert result.components["severity"].value is None
    assert "magnitude_unknown" in result.gaps
    assert "severity_unknown" in result.gaps
    assert result.components["magnitude"].facts["estimated_cases"] is None
    assert result.components["severity"].facts["reported_deaths"] is None


def test_explicit_death_and_severe_symptom_are_traceable_to_their_origins() -> None:
    death = calculate(signal(deaths=1), [record(1, deaths=1)])
    severe_symptom = calculate(
        signal(symptoms=("dificuldade para respirar",), cases=2),
        [record(1, cases=2, symptoms=("dificuldade para respirar",))],
    )

    assert death.components["severity"].value == 1
    assert death.components["severity"].origin_ids == (uid(1),)
    assert severe_symptom.components["severity"].value == 0.6
    assert severe_symptom.components["severity"].facts["severe_symptoms"] == [
        "dificuldade para respirar"
    ]


def test_conflicts_reduce_confidence_and_remain_visible_in_explanation() -> None:
    consistent = calculate(signal(), [record(1)])
    conflicting = calculate(
        signal(divergences=("magnitude_values_differ", "location_values_differ")),
        [record(1)],
    )

    assert conflicting.components["consistency"].value < consistent.components["consistency"].value
    assert conflicting.confidence < consistent.confidence
    assert conflicting.components["consistency"].facts["divergences"] == [
        "location_values_differ",
        "magnitude_values_differ",
    ]


def test_completeness_lists_known_and_missing_fields_without_clinical_inference() -> None:
    result = calculate(
        signal(cases=None, deaths=None),
        [record(1, cases=None, deaths=None)],
    )

    component = result.components["completeness"]
    assert component.value == 4 / 6
    assert component.facts == {
        "known_fields": ["condition", "geography", "symptoms", "temporal"],
        "missing_fields": ["magnitude", "severity"],
    }


def test_same_input_is_idempotent_and_new_policy_preserves_a_distinct_identity() -> None:
    first = calculate(signal(), [record(1)])
    repeated = calculate(signal(), [record(1)])
    revised = calculate(
        signal(),
        [record(1)],
        policy=PriorityPolicy.v1(
            version="priority-v2",
            weights=PriorityWeights(severity=0.25, corroboration=0.15),
        ),
    )

    assert first.id == repeated.id
    assert first.identity_key == repeated.identity_key
    assert revised.id != first.id
    assert revised.policy_version == "priority-v2"
    assert revised.signal_identity_key == first.signal_identity_key


def test_result_carries_the_complete_auditable_policy_configuration() -> None:
    result = calculate(signal(), [record(1)])

    assert result.configuration["version"] == "priority-v1"
    assert result.configuration["weights"]["severity"] == 0.2
    assert result.configuration["thresholds"] == {"attention": 35, "prompt": 65}
    assert result.configuration["recency_days"] == [2, 7, 14, 30]
    assert "dificuldade para respirar" in result.configuration["severe_symptoms"]


def test_triage_band_boundaries_are_inclusive_and_reproducible() -> None:
    policy = PriorityPolicy.v1(
        version="geography-only-v1",
        weights=PriorityWeights(
            corroboration=0,
            recency=0,
            geography=1,
            magnitude=0,
            severity=0,
            completeness=0,
            consistency=0,
        ),
        attention_threshold=50,
        prompt_threshold=75,
    )

    country = calculate(signal(), [record(1, precision="country")], policy=policy)
    state = calculate(signal(), [record(1, precision="state")], policy=policy)
    district = calculate(signal(), [record(1, precision="district")], policy=policy)

    assert (country.score, country.band) == (25, TriageBand.ROUTINE)
    assert (state.score, state.band) == (50, TriageBand.ATTENTION)
    assert (district.score, district.band) == (100, TriageBand.PROMPT)


def test_documented_manual_examples_match_the_implemented_formula() -> None:
    corroborated = calculate(
        signal(record_ids=(1, 2)),
        [record(1), record(2, source_name="fonte-b")],
        [PriorityRelation(uid(102), RelationKind.CORROBORATES, (uid(1), uid(2)))],
    )
    old_incomplete = calculate(
        signal(period_end=date(2026, 7, 1), cases=None, deaths=None),
        [record(1, precision="country", cases=None, deaths=None)],
    )

    assert (corroborated.score, corroborated.band, corroborated.confidence) == (
        78,
        TriageBand.PROMPT,
        88,
    )
    assert (old_incomplete.score, old_incomplete.band, old_incomplete.confidence) == (
        29,
        TriageBand.ROUTINE,
        77,
    )
