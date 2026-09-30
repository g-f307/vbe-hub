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
  - backend/src/vbe_hub/evaluation/relation_dataset.py
  - backend/src/vbe_hub/evaluation/relation_experiment.py
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

Para repetir uma nova versão do experimento com o Gemini, informando o commit avaliado:

```bash
EVALUATION_COMMIT=$(git rev-parse --short HEAD) docker compose --profile live run --rm correlation-live-evaluate
```

O comando gera JSON e Markdown em `data/reports/`. Esses artefatos locais não devem conter chave,
payload bruto ou dados reais. Somente um relatório pequeno e sanitizado da rodada aprovada deve
ser versionado posteriormente.

## Estado da evidência

O avaliador, as metas e o caminho Docker estão implementados e testados. A decisão final da
macroentrega 1 — aprovar, aprovar com ressalvas ou bloquear — depende da execução reservada com o
arquivo de entrada congelado; não deve ser inferida dos testes unitários perfeitos.

## Rodada reservada de 30/09/2026

A execução `276280372db6ee26`, no commit `fa7d1e3`, usou o dataset
`correlation-reserved-v1` (SHA-256
`4bb57293c7bfde7a865d13d306f22e32a40c2fa00297ad47d59a7285eee941b4`),
`gemini-embedding-001` e `gemini-3.5-flash-lite`.

| Métrica | Meta | Resultado | Situação |
| --- | ---: | ---: | --- |
| Recall de candidatos | ≥ 0,90 | 1,000000 | atende |
| Redução de pares | ≥ 0,80 | 0,911111 | atende |
| Macro-F1 | ≥ 0,75 | 0,733333 | não atende |
| Falhas operacionais | ≤ 0,05 | 0,000000 | atende |

Foram selecionados 4 de 45 pares, sem falsos negativos na seleção. O classificador confundiu o
único caso `corroborates` com `related_context`; por isso, F1 de `corroborates` foi 0 e F1 de
`related_context` foi 0,666667. Houve três chamadas ao modelo, 1.204 tokens de entrada, 219 de
saída, latência p50 de 1.125 ms e p95 de 1.327 ms. O custo permanece indisponível porque os preços
por milhão de tokens não foram configurados.

**Decisão:** bloquear a aprovação da macroentrega 1 nesta versão. O ajuste deve ocorrer sobre uma
nova calibração e produzir nova versão de prompt/política antes de outra avaliação; esta evidência
reservada não deve ser sobrescrita. A amostra contém somente 10 fichas sintéticas e avalia seleção
e relação sobre fichas predefinidas, não a qualidade da extração nem validade clínica.

## Correção metodológica da issue #40

O dataset `relation-*-v3` usa períodos distintos para calibração (2025) e avaliação (2026), IDs e conteúdo separados, 50 relações por classe no reservado e quatro negativos por alvo. Inclui corroboração sem doença nomeada, divergência de magnitude, campanhas e orientações, atualização posterior, republicação parafraseada, incompatibilidade geográfica, ausência de data/local e conteúdo instrucional adversarial tratado como dado não confiável. Inputs e gold são serializados e hasheados separadamente; gold só é lido após as predições.

A execução registra concorrência e tentativas do provider na identidade. O padrão conservador atual é concorrência `1`, até `3` tentativas e timeout de 60 s.

```bash
EVALUATION_COMMIT=$(git rev-parse --short HEAD) docker compose --profile live run --build --rm relation-calibrate
EVALUATION_COMMIT=$(git rev-parse --short HEAD) docker compose --profile live run --build --rm relation-live-evaluate-v3
```

## Estado da decisão em 30/09/2026

A rodada v2 (`6164a61a98a12346`) atingiu macro-F1 0,948622 e 0,938812, mas foi bloqueada por falhas operacionais de 7,6% e 14,8%. Ela foi depois considerada metodologicamente superseded porque havia repetição de padrões de conteúdo entre os splits.

O código v3 corrige essa sobreposição e cobre os casos difíceis. A nova calibração não pôde ser concluída: a API retornou `temporarily_unavailable` em 43/44 chamadas no modelo 3.5 e 44/44 no 2.5, com zero ou quase zero tokens, indicando cota do projeto indisponível. Portanto a Macroentrega 1 continua bloqueada; não há avaliação reservada v3 válida até a cota ser restabelecida.

[Voltar ao índice da documentação](README.md)
