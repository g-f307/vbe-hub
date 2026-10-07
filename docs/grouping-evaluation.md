---
id: TEST-004
type: testing
status: active
title: Avaliação de agrupamentos e efeito da revisão humana
created: 2026-10-07
updated: 2026-10-07
owner: VBE Hub
implemented_code:
  - backend/src/vbe_hub/evaluation/grouping_metrics.py
  - backend/src/vbe_hub/evaluation/grouping_dataset.py
  - backend/src/vbe_hub/evaluation/grouping_experiment.py
related_docs:
  - TEST-003
  - API-005
  - API-007
---

# Avaliação de agrupamentos e efeito da revisão humana

## Pergunta respondida

O experimento verifica se a política `signal-consolidation-v1` organiza relações já classificadas
em sinais correspondentes aos eventos sintéticos de referência, identifica quando dois eventos são
unidos indevidamente e mede o efeito de uma revisão humana. Ele não repete chamadas ao Gemini e não
mede diagnóstico, risco epidemiológico ou utilidade em uma operação real.

Em linguagem operacional: foi verificado se relatos pertencentes ao mesmo acontecimento aparecem
juntos, se acontecimentos diferentes permanecem separados e se um analista consegue corrigir uma
união automática errada sem apagar o histórico.

## Protocolo congelado

- dataset reservado `grouping-evaluation-v2`, semente `5170`;
- 60 eventos de referência e 270 registros sintéticos;
- 10 eventos em cada um de seis cenários: completo, doença ausente, local incompleto, data parcial,
  ponte conflitante e ponte contextual fraca;
- 60 relações `duplicate`, 92 `corroborates`, 60 `updates` e uma `related_context` no resultado
  automático;
- entradas e gold produzidos e serializados separadamente; `gold_event_id` não existe no objeto
  entregue ao consolidador;
- comparação do resultado automático com o resultado após uma rejeição humana sintética;
- 500 reamostragens bootstrap sobre registros para os intervalos exploratórios de 95%;
- metas definidas antes da rodada v2: F1 par a par, F1 B-cubed, pureza e cobertura ≥ 0,95; taxas de
  merge e split ≤ 0,05.

Calibração e reservado usam anos, sementes, IDs e conteúdo diferentes. Os testes automatizados
impedem sobreposição de registros e exigem ao menos 50 exemplos para cada relação positiva.

## Como interpretar as medidas

| Medida | Tradução para a vigilância |
| --- | --- |
| Precisão par a par | Entre os pares colocados juntos, quantos realmente pertenciam ao mesmo evento. |
| Recall par a par | Entre os pares do mesmo evento, quantos permaneceram juntos. |
| B-cubed | Equilibra, registro a registro, contaminação e fragmentação dos grupos. |
| Pureza | Quanto cada sinal contém registros de um único evento de referência. |
| Cobertura/inverse purity | Quanto cada evento de referência foi preservado em um único sinal. |
| Merge | Dois ou mais eventos diferentes foram reunidos no mesmo sinal. |
| Split | Um único evento foi fragmentado em sinais diferentes. |

Esses números avaliam organização técnica de dados sintéticos. Eles não expressam sensibilidade de
vigilância, probabilidade de surto ou prioridade clínica.

## Rodada reservada válida de 7 de outubro de 2026

Identidade `a23f1eb5c9300765`, commit `a64f4df`.

- SHA-256 das entradas: `85f97c612163692871fc6d9bda6f790c17c5847664f03988e8e83e4689b40728`;
- SHA-256 do gold separado: `226893ebf42d422c23be4d9b1913eae10506254a7dde0b59c4b91ebfc0c540c7`.

| Resultado | Precisão par | Recall par | F1 par | F1 B-cubed | Pureza | Cobertura | Merges | Splits |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Automático | 0,967742 | 1,000000 | 0,983607 | 0,992537 | 0,985185 | 1,000000 | 1 | 0 |
| Após revisão | 1,000000 | 1,000000 | 1,000000 | 1,000000 | 1,000000 | 1,000000 | 0 | 0 |

O intervalo bootstrap de 95% foi `[0,963797; 1,000000]` para F1 par a par e
`[0,987889; 1,000000]` para F1 B-cubed no resultado automático. Após a revisão, ambos ficaram em
`[1,000000; 1,000000]` nesta amostra construída.

### Cadeia causal do erro

O resultado automático uniu `evaluation-event-000` e `evaluation-event-012`. A relação sintética
incorreta `6420c6b7-9572-50f6-ba6d-4e1bc47fe3a6`, classificada como `corroborates`, foi a primeira
causa conhecida. O consolidador agiu conforme sua entrada; portanto, o erro foi atribuído à etapa
de relação, não escondido como falha de agrupamento. A revisão humana sintética rejeitou essa
relação com o motivo `different_event`; o reprocessamento separou os sinais e eliminou o merge.

O cenário `complete`, que continha os dois eventos afetados, teve F1 par a par 0,882353 antes da
revisão e 1,000000 depois. Os outros cinco cenários tiveram F1 1,000000, sem merges ou splits. Isso
mostra por que a análise por cenário é necessária mesmo quando a média global atende à meta.

## Operação e custo

A rodada executou somente dados e relações sintéticas congeladas: zero chamadas ao provider, zero
tokens, zero falhas e custo externo zero. Latência de IA não se aplica. Qualidade, falhas e consumo
da correlação com Gemini permanecem na [avaliação de correlação](correlation-evaluation.md), cuja
rodada exploratória foi aprovada com ressalvas. As duas evidências não devem ser somadas como se
fossem uma validação ponta a ponta sobre fontes reais.

## Decisão e limitações

**Decisão: aprovar com ressalvas a política de agrupamento para a PoC sintética.** Todas as metas
congeladas da rodada v2 foram atendidas, e a revisão removeu o erro controlado sem modificar o gold.

As ressalvas são materiais:

- as relações de entrada são sintéticas e congeladas, não novas respostas do Gemini;
- o erro foi injetado deliberadamente para testar rastreabilidade e correção;
- o bootstrap sobre registros descreve somente esta população sintética;
- não houve repetição de provider porque esta etapa não chama provider;
- a evidência não demonstra validade clínica, epidemiológica ou generalização para EIOS/GdS.

A execução preliminar `grouping-evaluation-v1`, com 210 registros, foi invalidada antes da conclusão
porque continha somente 30 relações `updates`, abaixo da meta prévia de 50. Ela não é usada na
decisão. O redimensionamento gerou `v2`, novos hashes e nova identidade, preservando a transparência
da alteração.

## Reprodução

Com o repositório no commit avaliado:

```bash
EVALUATION_COMMIT=$(git rev-parse --short HEAD) \
  docker compose --profile tools run --build --rm grouping-evaluate
```

O comando grava JSON, Markdown e CSV de erros sanitizados em `data/reports/`, diretório ignorado
pelo Git. Os artefatos contêm somente IDs e conteúdo sintéticos; não incluem credenciais, respostas
brutas de provider ou narrativas reais.
