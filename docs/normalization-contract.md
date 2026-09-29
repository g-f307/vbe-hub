---
id: API-002
type: api
status: active
title: Contrato de normalização
created: 2026-09-29
updated: 2026-09-29
owner: VBE Hub
implemented_code:
  - backend/src/vbe_hub/normalization/
  - backend/tests/fixtures/normalization/
related_docs:
  - API-001
  - DATA-001
  - DES-001
---

# Contrato de normalização

## Finalidade

A normalização converte envelopes heterogêneos em uma representação determinística comum antes de
qualquer extração por IA. Ela organiza valores fornecidos pela fonte, mas não infere doença,
patógeno, síndrome, relevância epidemiológica nem relações entre registros.

O resultado é armazenado em `normalized_records` com a versão do normalizador. A versão inicial é
`1.0.0`.

## Estrutura comum

| Campo | Tipo | Regra |
| --- | --- | --- |
| `source_kind` | `media` ou `community` | Preserva o tipo da origem. |
| `source_name` | texto | Preserva o nome da fonte. |
| `external_id` | texto ou nulo | Preserva a identidade externa. |
| `published_at` | data/hora | ISO 8601 convertido para UTC. |
| `language` | texto | Tag normalizada, por exemplo `PT_br` para `pt-BR`. |
| `title` | texto ou nulo | Não é criado para fontes sem título. |
| `text` | texto | Narrativa original usada nas próximas etapas. |
| `location` | objeto | País, estado, município, distrito, local específico e precisão. |
| `magnitude` | objeto | Casos e óbitos estimados, como inteiros não negativos ou nulos. |
| `symptoms` | lista de texto | Lista vazia significa que nenhum sintoma foi fornecido. |
| `affected_group` | texto ou nulo | Grupo agregado informado pela fonte. |
| `environment` | texto ou nulo | Ambiente agregado informado pela fonte. |
| `metadata` | objeto | URL, janela reportada e tópico declarados pela fonte. |

`location` sempre contém `country`, `state`, `municipality`, `district`, `specific` e `precision`.
`magnitude` sempre contém `estimated_cases` e `estimated_deaths`. `metadata` sempre contém
`source_url`, `reported_window_start`, `reported_window_end` e `topic`. Essa estabilidade permite
que mídia e comunidade alimentem o mesmo pipeline.

## Adaptação por fonte

- Mídia prioriza `district` e aceita `neighborhood` como alias.
- Comunidade prioriza `neighborhood`, normalizado como `district`, e aceita `district` como alias.
- Precisões `neighborhood` e `exact` são normalizadas para `district` e `specific`.
- Janelas de relato aceitam datas ISO 8601 com fuso e são convertidas para UTC.

Os contratos atuais são sintéticos e não afirmam reproduzir endpoints oficiais de EIOS ou
Guardiões da Saúde. Adaptadores reais exigirão revisão deste mapeamento.

## Nulos e erros

Campo ausente, vazio ou explicitamente desconhecido permanece nulo. Em particular, magnitude
desconhecida nunca se torna zero, e precisão `unknown` torna-se nula. O normalizador não geocodifica
nem completa localidades.

Tipo inválido, magnitude negativa, precisão não suportada ou data sem fuso produz um
`NormalizedRecord` com estado `failed`, código `invalid_field`, mensagem sanitizada e dados
normalizados vazios. Os demais registros do lote continuam sendo processados. Resultados válidos
recebem estado `succeeded` e preservam o UUID do registro bruto em `raw_record_id`.

## Evidência reproduzível

O teste de contrato usa os dois primeiros envelopes de
`backend/tests/fixtures/synthetic/v1/records.jsonl` e compara o resultado com
`backend/tests/fixtures/normalization/v1/expected.json`. Assim, a fixture cobre mídia e comunidade
sem reutilizar a implementação para calcular a expectativa.
