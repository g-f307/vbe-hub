---
id: API-005
type: api
status: active
title: Consolidação de sinais de alerta
created: 2026-10-02
updated: 2026-10-07
owner: VBE Hub
implemented_code:
  - backend/src/vbe_hub/application/correlation/signals.py
  - backend/src/vbe_hub/adapters/persistence/signal_repository.py
related_docs:
  - API-004
  - DATA-001
  - ADR-006
  - TEST-004
---

# Consolidação de sinais de alerta

## Finalidade e limite

A consolidação transforma as relações previamente classificadas entre fichas técnicas em sinais
de alerta auditáveis. O resultado organiza evidências para revisão; não confirma um surto, não
define prioridade sanitária e não substitui a avaliação do profissional de vigilância.

## Entradas

O caso de uso recebe fichas técnicas identificadas e avaliações de relação já persistidas. A
política de agrupamento também é entrada explícita e possui versão. A primeira versão considera:

- `duplicate`, `corroborates` e `updates` como relações fortes capazes de unir componentes;
- `related_context` apenas como contexto, sem permitir que uma evidência fraca una dois grupos;
- `unrelated` e avaliações que falharam como incapazes de agrupar registros;
- distância temporal máxima configurável, com padrão de 14 dias.

## Regras de segurança do agrupamento

Antes de aceitar cada relação forte, o serviço compara todos os registros dos dois componentes.
Conflitos fortes impedem a união e são registrados com códigos estáveis:

| Código | Significado |
| --- | --- |
| `geographic_conflict` | Municípios informados e diferentes. |
| `clinical_conflict` | Doenças ou condições informadas e diferentes. |
| `temporal_conflict` | Inícios separados por mais dias que o limite da política. |
| `weak_bridge_blocked` | Relação apenas contextual tentaria unir componentes independentes. |

Campos ausentes não são tratados como conflito e nenhum valor é inferido para preenchê-los. A
ordem de entrada não altera o identificador nem o conteúdo consolidado.

## Conteúdo do sinal

Cada sinal guarda a versão da política, estado de processamento, membros centrais, membros de
contexto, relações utilizadas e conflitos rejeitados. Período, localização, sintomas, condições e
magnitude são derivados somente das fichas centrais e mantêm a proveniência dos registros de
origem. Valores distintos permanecem visíveis como divergências. Em relações `updates`, o valor
mais recente pode representar a magnitude atual, mas o histórico anterior não é descartado.

Título e resumo são determinísticos e descritivos. Eles não contêm diagnóstico novo nem juízo de
risco. O estado inicial é `suggested`, reservado à triagem humana posterior.

## Idempotência e versionamento

A identidade é calculada a partir da versão da política e dos membros centrais e contextuais
ordenados. Reprocessar as mesmas entradas com a mesma política atualiza a mesma identidade;
alterar a política produz uma nova versão coexistente, preservando o histórico.

## Exemplo sanitizado

```json
{
  "policy_version": "signal-consolidation-v1",
  "processing_state": "suggested",
  "title": "Sarampo em Manaus",
  "core_record_ids": ["00000000-0000-0000-0000-000000000101", "00000000-0000-0000-0000-000000000102"],
  "context_record_ids": ["00000000-0000-0000-0000-000000000103"],
  "conditions": ["sarampo"],
  "symptoms": ["febre", "manchas vermelhas"],
  "current_estimated_cases": 12,
  "divergence_codes": ["magnitude_divergence"]
}
```

Os identificadores são fictícios e o exemplo não representa pessoas ou ocorrência real.

## Validação automatizada

Os testes unitários cobrem agrupamento forte, atualização de magnitude, contexto sem transitividade,
conflitos, falhas e identidade versionada. Os testes de integração usam PostgreSQL real para validar
migration, idempotência, coexistência entre versões, vínculos com origens e recuperação de conflitos.

A rodada reservada sintética `grouping-evaluation-v2` avaliou 60 eventos e 270 registros, incluindo
um merge controlado e sua correção humana. Consulte a [avaliação de
agrupamentos](grouping-evaluation.md) para protocolo, resultados e limitações.
