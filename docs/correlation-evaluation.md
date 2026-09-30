---
id: TEST-003
type: testing
status: active
title: Avaliação da correlação
created: 2026-09-30
updated: 2026-09-30
owner: VBE Hub
implemented_code:
  - backend/src/vbe_hub/evaluation/correlation_metrics.py
  - backend/src/vbe_hub/evaluation/correlation_protocol.py
  - backend/src/vbe_hub/evaluation/correlation_report.py
  - backend/src/vbe_hub/evaluation/correlation_command.py
related_docs:
  - API-005
  - API-006
  - API-007
  - TEST-001
---

# Avaliação da correlação

O protocolo mede separadamente recuperação de candidatos e classificação. Gold é lido somente
pelo avaliador; nunca entra em embeddings, filtros ou julgamento.

## Metas prévias da macroentrega 1

- recall de relações positivas nos candidatos ≥ 0,90;
- redução do total teórico de pares ≥ 0,80;
- macro-F1 da classificação ≥ 0,75;
- taxa de falha operacional ≤ 0,05;
- todos os erros rastreáveis apenas por identificadores sintéticos.

Essas metas devem ser aplicadas primeiro à calibração. A configuração é então congelada antes da
avaliação reservada. Observar o reservado e alterar limiar/prompt exige nova versão e não apaga a
rodada anterior.

## Entrada e identidade

`data/evaluation/correlation-input.json` contém `experiment`, `theoretical_pairs`, `cases` e
`operations`. A identidade SHA-256 inclui dataset, split, seed, commit, versões dos modelos e da
representação, política temporal/geográfica e todos os limiares. Os casos usam somente IDs
sintéticos, gold, decisão/predição e causa de exclusão ou falha; narrativas não são publicadas.

## Métricas

- candidatos: precisão, recall, redução de pares e falsos negativos por causa;
- classificação: precisão/recall/F1 por classe, macro/micro-F1 e matriz de confusão completa;
- operação: chamadas reais, cache, p50/p95, unidades e custo estimado.

Falha do provider fica fora da matriz como falha e não é convertida em `unrelated`. Cache hit não
conta como chamada nem custo adicional.

## Reprodução

```bash
mkdir -p data/evaluation data/reports
docker compose --profile tools run --rm correlation-evaluate
```

O comando gera JSON e Markdown em `data/reports/`. Esses artefatos locais não devem conter chave,
payload bruto ou dados reais. Somente um relatório pequeno e sanitizado da rodada aprovada deve
ser versionado posteriormente.

## Estado da evidência

O avaliador, as metas e o caminho Docker estão implementados e testados. A decisão final da
macroentrega 1 — aprovar, aprovar com ressalvas ou bloquear — depende da execução reservada com o
arquivo de entrada congelado; não deve ser inferida dos testes unitários perfeitos.

[Voltar ao índice da documentação](README.md)
