---
id: API-009
type: api
status: active
title: Métricas operacionais e evidências sintéticas
created: 2026-10-26
updated: 2026-10-26
owner: VBE Hub
implemented_code:
  - backend/src/vbe_hub/api/metrics.py
related_docs:
  - API-008
  - TEST-002
  - TEST-003
  - TEST-004
  - DES-001
---

# Métricas operacionais e evidências sintéticas

## Finalidade

`GET /metrics/summary` oferece um contrato reconciliável para indicadores do painel. Ele separa
contagens da execução local, qualidade técnica medida em avaliações sintéticas e qualquer
interpretação epidemiológica. Esta última não é produzida pelo endpoint: nenhum número confirma
diagnóstico, surto, risco ou prioridade sanitária.

O resumo é calculado sob demanda a partir de agregados do PostgreSQL. A consulta não materializa
payloads individuais e não retorna narrativa, fonte real, gabarito reservado ou credencial.

## Identidade e estado

A resposta identifica `metrics-summary-v1`, o instante de cálculo e a classificação
`technical_operational`. `operational_status` possui três estados:

- `empty`: nenhuma entrada persistida;
- `ok`: há dados, sem falha registrada e sem diferença nos pontos reconciliados;
- `partial_failure`: existe falha de etapa, execução com falha ou lacuna/excesso no funil.

O bloco `dataset` permanece `unavailable` quando não há proveniência, `single` quando todos os
registros pertencem à mesma combinação gerador/versão/semente e `mixed` quando mais de uma
combinação está presente. `mixed` não é convertido silenciosamente em um dataset único.

## Janela e defasagem

`window.start` e `window.end` são o menor e o maior `published_at` dos registros de origem.
`latest_activity_at` considera a última escrita relevante do funil, prioridade ou revisão.
`lag_seconds` é calculado no instante da consulta. `freshness` é `unavailable` sem atividade,
`current` para atividade há no máximo sete dias e `stale` acima desse limite. Defasagem indica
idade técnica do dado, não ausência de evento de saúde.

## Funil persistido

`pipeline` expõe valor, estado e origem reconciliável para registros brutos, normalizações, fichas,
pares avaliados, relações, sinais, prioridades e revisões. Zero com banco populado é uma contagem
disponível. Banco vazio usa `status: empty`. A ausência de amostras de duração usa `unavailable` e
`null`, nunca zero inventado.

As durações de extração e relação informam amostras, média e máximo em milissegundos. O último
`processing_run`, quando existente, preserva ID, tipo, estado, período, duração, contagens e versões
dos componentes; sem execução, o bloco usa `status: unavailable`.

## Reconciliação automática

| Chave | Esperado | Observado |
| --- | --- | --- |
| `normalization_coverage` | registros de origem | origens com normalização bem-sucedida |
| `extraction_coverage` | origens normalizadas com sucesso | normalizações com ficha bem-sucedida |
| `priority_coverage` | sinais consolidados | sinais com ao menos uma prioridade persistida |

`balanced` significa igualdade; `gap` significa menos resultados que entradas; `excess` indica
mais resultados distintos que o esperado; sem entrada, o estado é `unavailable`. A diferença é
sempre `observed - expected`.

## Evidências de avaliação

`evaluations` contém somente sínteses sanitizadas e versionadas das evidências oficiais:

- ficha técnica `3260ec0dc1945093`, bloqueada pela falha operacional e pela amostra pequena;
- correlação `ce77f037927356db`, aprovada com ressalvas como evidência exploratória;
- agrupamento `a23f1eb5c9300765`, aprovado com ressalvas sobre dados sintéticos congelados.

Cada item informa identidade, versão do dataset, data, decisão, nível de evidência, artefato
documental, medidas selecionadas, escopo e limitação. `null` em custo significa indisponível, não
custo zero. Inputs, gold, IDs de registros e casos individuais continuam fora da API.

## Interpretação para profissionais de saúde

As contagens respondem “quanto o protótipo processou e o que ficou pendente?”. A reconciliação
responde “alguma etapa recebeu itens e produziu menos resultados do que o esperado?”. As
avaliações respondem “como uma versão identificada se comportou numa prova sintética controlada?”.

Nenhum desses grupos responde se existe um surto, se um agravo foi confirmado ou qual resposta
sanitária deve ser adotada. Essas conclusões permanecem sob análise profissional e dependem das
evidências de origem.
