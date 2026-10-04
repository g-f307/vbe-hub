---
id: DATA-001
type: data
status: active
title: Modelo persistente inicial
created: 2026-09-28
updated: 2026-10-03
owner: VBE Hub
implemented_code:
  - backend/migrations/
  - backend/src/vbe_hub/adapters/persistence/
related_docs:
  - API-001
  - DES-001
  - ADR-003
  - ADR-005
  - API-004
  - API-005
  - ADR-006
  - API-006
  - ADR-007
---

# Modelo persistente inicial

## Fronteiras

As entidades em `vbe_hub.domain` não dependem do banco. Interfaces de repositório pertencem à camada de aplicação; modelos SQLAlchemy, consultas e conversões ficam em adapters. PostgreSQL é a fonte persistente e Alembic controla sua evolução.

## Schema

| Tabela | Finalidade | Relações e restrições principais |
| --- | --- | --- |
| `processing_runs` | Execuções de ingestão ou processamento e contadores auditáveis. | Estado controlado; contadores não negativos. |
| `raw_records` | Envelope e payload original de mídia ou comunidade. | FK opcional para execução; tipo de fonte controlado; hash SHA-256. |
| `record_provenance` | Adaptador, gerador, semente, cenário e coleta. | Relação 1:1 obrigatória com registro bruto. |
| `normalized_records` | Resultado versionado ou falha estruturada da normalização. | FK indexada; unicidade por registro e versão do normalizador. |
| `evaluation_labels` | Gabarito sintético reservado à avaliação. | Relação 1:1 com registro bruto; nunca consultada pelo repositório do pipeline. |
| `technical_sheet_extractions` | Ficha validada ou última falha por configuração de extração. | FK indexada para normalização; chave de cache única; hashes e consumo validados. |
| `consolidated_signals` | Sinal derivado e versionado, com campos agregados e proveniência. | Identidade única por política e origens; estado controlado. |
| `signal_members` | Registros centrais ou contextuais que compõem o sinal. | Unicidade por sinal e registro; FKs indexadas e papel controlado. |
| `signal_relation_links` | Avaliações de relação aceitas como suporte ou contexto. | Unicidade por sinal e avaliação; FKs indexadas. |
| `signal_grouping_conflicts` | Uniões rejeitadas pela política de agrupamento. | Unicidade por política, avaliação e código; origens e detalhes preservados. |
| `suggested_priorities` | Cálculo explicável e versionado para ordenar a triagem. | FK para o sinal; identidade única; score, confiança e faixa controlados; componentes e lacunas em JSONB. |

Todos os identificadores de tabela e coluna usam `snake_case`. Datas são `timestamptz`; payloads e erros estruturados usam `jsonb`. FKs usadas em consulta possuem índices explícitos.

## Idempotência

A identidade externa é avaliada dentro de `(source_kind, source_name)`:

- com `external_id`, a combinação `(source_kind, source_name, external_id)` é única;
- sem `external_id`, a combinação `(source_kind, source_name, content_hash)` é única;
- repetir a mesma chave com o mesmo hash retorna o registro existente;
- reutilizar um `external_id` com conteúdo diferente gera conflito explícito e não sobrescreve a auditoria.

O hash é SHA-256 de uma representação canônica do conteúdo, com chaves JSON ordenadas. Fontes distintas podem corroborar o mesmo texto sem serem deduplicadas indevidamente.

A extração usa chave SHA-256 própria sobre entrada, provedor, modelo e versões de prompt/schema.
O upsert por essa chave permite substituir falha por sucesso sem criar fichas duplicadas.

A identidade do sinal usa a versão da política e a lista canônica de membros centrais e
contextuais. A mesma política e as mesmas origens atualizam o mesmo sinal; uma nova versão da
política cria outro sinal e preserva o anterior. Membros, avaliações aceitas e conflitos apontam
para os registros e avaliações originais, sem cópias que rompam a rastreabilidade.

A prioridade referencia o sinal persistido e também registra sua identidade e versão como snapshot.
A identidade do cálculo inclui a configuração completa e o instante de referência. Repetições são
idempotentes; novas políticas ou recálculos coexistem. A justificativa contém apenas fatos
estruturados, IDs de origem e relações, sem payload bruto.

## Isolamento do gabarito

`gold_event_id` existe somente em `EvaluationLabel` e `evaluation_labels`. `RawRecord`, `StoredRawRecord` e o repositório entregue ao pipeline não possuem esse atributo. Acesso ao gabarito exige o adapter de avaliação separado.

## Limites atuais

Usuários, decisões humanas de triagem e retenção de dados reais não pertencem a este schema.
Backup também não está previsto nesta etapa; volumes Docker são persistência de desenvolvimento,
não estratégia de recuperação.
