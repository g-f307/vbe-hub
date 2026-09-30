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
  - REPORT-001
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

O dataset `relation-*-v3` usa períodos distintos para calibração (2025) e avaliação (2026), IDs e conteúdo separados e quatro negativos por alvo. O gerador mantém capacidade para 50 relações por classe, mas a execução Docker padrão usa temporariamente 10 por classe para respeitar a cota gratuita. Inclui corroboração sem doença nomeada, divergência de magnitude, campanhas e orientações, atualização posterior, republicação parafraseada, incompatibilidade geográfica, ausência de data/local e conteúdo instrucional adversarial tratado como dado não confiável. Inputs e gold são serializados e hasheados separadamente; gold só é lido após as predições.

A identidade registra concorrência, tentativas do provider, quantidade de repetições e a política de ordenação. Antes de cada rodada, os pares são embaralhados deterministicamente com a seed registrada; assim, uma interrupção da API não fica concentrada em classes contíguas e a execução continua reprodutível. O padrão conservador é concorrência `1`, até `3` tentativas e timeout de 60 s.

## Protocolo exploratório com cota gratuita

A avaliação reservada padrão contém 10 casos por classe, totalizando 50 relações gold, 250 pares de entrada e uma repetição. A taxa de falha operacional usa como denominador somente os pares efetivamente enviados ao provider, incluindo respostas inválidas ou indisponíveis; decisões determinísticas não entram no denominador. A política de candidatos reduz as chamadas: na calibração anterior, 44 pares chegaram ao Gemini. Esse número é uma estimativa, não uma garantia de consumo, pois depende das decisões determinísticas do seletor.

O resultado deve ser interpretado como evidência técnica **exploratória**. Mesmo que todas as metas sejam atingidas, uma única rodada pequena não mede estabilidade entre repetições nem substitui a avaliação ampliada. Quando houver cota ou orçamento adequado, a capacidade de 50 casos por classe e duas repetições permanece disponível para evidência mais robusta.

```bash
EVALUATION_COMMIT=$(git rev-parse --short HEAD) docker compose --profile live run --build --rm relation-calibrate
EVALUATION_COMMIT=$(git rev-parse --short HEAD) docker compose --profile live run --build --rm relation-live-evaluate-v3
```

Além do JSON e do Markdown agregados, cada execução grava `relation-<split>-<identidade>-provider-cases.csv` em `data/reports/`. O CSV contém apenas os pares efetivamente enviados ao provider, com relação gold, previsão, confiança, código de falha, justificativa validada e resumos sintéticos das duas fichas. Não contém chave, resposta bruta do provider ou dados reais e permanece fora do Git.

## Estado da decisão em 30/09/2026

A rodada v2 (`6164a61a98a12346`) atingiu macro-F1 0,948622 e 0,938812, mas foi bloqueada por falhas operacionais de 7,6% e 14,8%. Ela foi depois considerada metodologicamente superseded porque havia repetição de padrões de conteúdo entre os splits.

A calibração v3 com 10 casos por classe atingiu macro-F1 1,0 e teve duas falhas temporárias, dentro da meta operacional.

A avaliação exploratória `ec81883fbb0d8914` realizou 44 chamadas e registrou 28 falhas `temporarily_unavailable`. O relatório original calculou 57,1429% sobre 49 pares selecionados; a interpretação corrigida é 63,6364% sobre 44 chamadas reais. A evidência histórica não foi sobrescrita e continua bloqueada. Os 16 retornos do Gemini foram corretos, mas ficaram concentrados nas primeiras classes por causa da ordem anterior do dataset; por isso não sustentam conclusão geral. A tentativa ampliada de avaliação, com 50 casos por classe e duas repetições, exigia 220 chamadas ao provider por rodada e foi inviabilizada pela cota gratuita: 56,3% e 69,4% das chamadas falharam. As respostas que chegaram a ser processadas não bastam para uma conclusão válida sobre a amostra inteira.

A execução reservada corrigida `ce77f037927356db`, no commit `f5a57cb`, concluiu 44 chamadas sem falhas e classificou corretamente todos os casos, com recall de candidatos 1,0, redução de pares 0,804 e macro-F1 1,0. Todas as metas previamente congeladas foram atendidas. Assim, a capacidade de correlação da Macroentrega 1 foi **aprovada com ressalvas** como evidência técnica exploratória; a generalização estatística, a validade clínica e a validade epidemiológica continuam fora do que esta rodada permite afirmar.

[Consultar a síntese para profissionais de saúde](health-stakeholder-validation.md) · [Voltar ao índice da documentação](README.md)
