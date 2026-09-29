"""Deterministic generation of synthetic media and community signals."""

from __future__ import annotations

import hashlib
import json
import random
from datetime import UTC, datetime, time, timedelta
from uuid import NAMESPACE_URL, uuid5

from vbe_hub.synthetic.models import (
    ExpectedRelation,
    GeneratedRecord,
    GeneratorConfig,
    GoldLabel,
    RelationKind,
    ScenarioKind,
    SyntheticDataset,
)

_NARRATIVES: dict[ScenarioKind, tuple[str, str]] = {
    ScenarioKind.DUPLICATE: (
        "Boletim republicado",
        "Conteúdo sintético republica alerta sobre manchas vermelhas e febre.",
    ),
    ScenarioKind.CORROBORATION: (
        "Relatos corroboram alerta",
        "Relato sintético agregado informa várias pessoas com febre e manchas vermelhas.",
    ),
    ScenarioKind.UPDATE: (
        "Atualização do alerta",
        "Atualização sintética acrescenta nova estimativa agregada de casos.",
    ),
    ScenarioKind.RELATED_CONTEXT: (
        "Campanha preventiva",
        "Notícia sintética divulga vacinação preventiva, sem informar novos casos.",
    ),
    ScenarioKind.UNRELATED_TIME: (
        "Sintomas em período distinto",
        "Sinal sintético semelhante ocorreu em uma janela temporal incompatível.",
    ),
    ScenarioKind.UNRELATED_LOCATION: (
        "Sintomas em local distinto",
        "Sinal sintético semelhante ocorreu em uma localidade incompatível.",
    ),
    ScenarioKind.UNKNOWN_DISEASE: (
        "Agravo ainda desconhecido",
        "Relato sintético descreve febre e manchas, sem atribuir uma doença.",
    ),
    ScenarioKind.KNOWN_PARTIAL: (
        "Possível sarampo",
        "Notícia sintética cita sarampo, mas descreve somente parte dos sinais.",
    ),
    ScenarioKind.LOCATION_VARIATION: (
        "Localidade aproximada",
        "Relato sintético alterna entre município, bairro aproximado e local ausente.",
    ),
    ScenarioKind.DATE_VARIATION: (
        "Data aproximada",
        "Relato sintético usa data exata, intervalo ou expressão temporal relativa.",
    ),
    ScenarioKind.MAGNITUDE_VARIATION: (
        "Quantidade incerta",
        "Sinal sintético apresenta magnitude exata, aproximada, conflitante ou desconhecida.",
    ),
    ScenarioKind.IRRELEVANT: (
        "Atividade sem sinal epidemiológico",
        "Conteúdo sintético trata de atividade comunitária sem evento de saúde pública.",
    ),
}


def _config_fingerprint(config: GeneratorConfig) -> str:
    canonical = json.dumps(
        {
            "allowed_locations": config.allowed_locations,
            "end_date": config.end_date.isoformat(),
            "event_count": config.event_count,
            "generator_version": config.generator_version,
            "languages": config.languages,
            "media_ratio": config.media_ratio,
            "missing_field_rate": config.missing_field_rate,
            "noise_level": config.noise_level,
            "relation_distribution": sorted(
                (relation.value, weight)
                for relation, weight in config.relation_distribution.items()
            ),
            "scenario_kinds": [scenario.value for scenario in config.scenario_kinds],
            "seed": config.seed,
            "start_date": config.start_date.isoformat(),
            "total_records": config.total_records,
        },
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    return hashlib.sha256(canonical).hexdigest()[:12]


def _record_id(config: GeneratorConfig, fingerprint: str, index: int) -> str:
    return str(uuid5(NAMESPACE_URL, f"vbe-hub:{config.generator_version}:{fingerprint}:{index}"))


def _weighted_relation(rng: random.Random, config: GeneratorConfig) -> RelationKind:
    relations = tuple(config.relation_distribution)
    weights = tuple(config.relation_distribution[relation] for relation in relations)
    return rng.choices(relations, weights=weights, k=1)[0]


def generate_dataset(config: GeneratorConfig) -> SyntheticDataset:
    """Generate pipeline records and separate gold-standard metadata."""

    rng = random.Random(config.seed)
    fingerprint = _config_fingerprint(config)
    media_count = round(config.total_records * config.media_ratio)
    source_kinds = ["media"] * media_count + ["community"] * (
        config.total_records - media_count
    )
    rng.shuffle(source_kinds)
    period_days = (config.end_date - config.start_date).days

    records: list[GeneratedRecord] = []
    labels: list[GoldLabel] = []
    for index in range(config.total_records):
        scenario = config.scenario_kinds[index % len(config.scenario_kinds)]
        source_kind = source_kinds[index]
        record_id = _record_id(config, fingerprint, index)
        event_number = index % config.event_count
        gold_event_id = None if scenario is ScenarioKind.IRRELEVANT else f"event-{event_number:04d}"
        scenario_id = f"scenario-{index:06d}"
        published_date = config.start_date + timedelta(days=rng.randint(0, period_days))
        published_at = datetime.combine(published_date, time(12), tzinfo=UTC).isoformat()
        language = config.languages[index % len(config.languages)]
        municipality: str | None = config.allowed_locations[
            event_number % len(config.allowed_locations)
        ]
        if rng.random() < config.missing_field_rate:
            municipality = None
        title, body = _NARRATIVES[scenario]
        if rng.random() < config.noise_level:
            body = f"{body} Informação agregada pode conter grafia imprecisa."
        external_id = f"{source_kind}-{fingerprint}-{index:06d}"
        records.append(
            GeneratedRecord(
                id=record_id,
                source_kind=source_kind,
                source_name=(
                    "Agência Sentinela Sintética"
                    if source_kind == "media"
                    else "Canal Comunitário Sintético"
                ),
                external_id=external_id,
                published_at=published_at,
                title=title if source_kind == "media" else "Relato agregado sintético",
                body=body,
                source_url=f"https://dados-sinteticos.invalid/{external_id}",
                language=language,
                payload={
                    "municipality": municipality,
                    "symptoms": ["febre", "manchas vermelhas"],
                    "estimated_cases": None if index % 4 == 0 else 2 + (index % 19),
                    "geographic_precision": "municipality" if municipality else "unknown",
                    "synthetic": True,
                },
                provenance={
                    "generator": "vbe-hub",
                    "version": config.generator_version,
                    "seed": config.seed,
                },
            )
        )
        labels.append(
            GoldLabel(
                record_id=record_id,
                scenario_id=scenario_id,
                gold_event_id=gold_event_id,
                scenario_kind=scenario,
            )
        )

    relations = tuple(
        ExpectedRelation(
            left_record_id=records[index].id,
            right_record_id=records[index + 1].id,
            relation=_weighted_relation(rng, config),
        )
        for index in range(0, len(records) - 1, 2)
    )
    return SyntheticDataset(tuple(records), tuple(labels), relations)
