---
id: EVID-010
type: evidence
status: active
title: Avaliação dos sinais relacionados
created: 2026-11-08
updated: 2026-11-08
owner: VBE Hub
implemented_code:
  - backend/src/vbe_hub/evaluation/related_signals.py
  - backend/src/vbe_hub/evaluation/related_signals_command.py
  - backend/src/vbe_hub/evaluation/related_signals_live.py
related_docs:
  - ADR-010
  - DES-003
  - TEST-001
---

# Avaliação dos sinais relacionados

Voltar ao [índice da documentação](README.md).

## Objetivo

Esta avaliação verifica se a sugestão de sinais relacionados chega ao analista de forma rápida,
econômica, rastreável e compreensível. Ela não avalia diagnóstico, existência de surto ou validade
epidemiológica. A IA continua sendo apoio técnico: o vínculo entre sinais só passa a compor uma
ficha quando o profissional o confirma.

## O que é medido

O preparo assíncrono é separado em fila, extração, embedding, busca de candidatos e julgamento da
relação. A leitura da aba mede apenas a recuperação da sugestão persistida; portanto, abrir a aba
não chama a OpenAI nem fica aguardando uma resposta externa.

Os limites exploratórios desta PoC são:

| Verificação | Limite |
| --- | ---: |
| leitura de sugestão pronta, p95 | até 500 ms |
| preparo completo após a entrada, p95 | até 60 s |
| cobertura dos pares relacionados conhecidos | pelo menos 90% |
| macro F1 da classificação | pelo menos 0,75 |

P50 representa uma execução típica e p95 uma execução próxima das mais lentas. Para a equipe de
saúde, a interpretação útil é: a sugestão pronta deve abrir imediatamente; enquanto ela não existe,
o sistema deve dizer `pending`; quando o provedor falha, deve dizer `failed` e nunca transformar a
falha em decisão sanitária.

## Dois níveis de evidência

### Fixture reproduzível, sem consumo de API

O arquivo `related-signals-recorded-v1.json` é uma fixture de contrato. Seus valores gravados
exercitam percentis, custos, cache, limites e a tradução para a equipe de saúde. Ele não comprova a
latência atual da OpenAI nem a qualidade atual de um modelo.

```bash
EVALUATION_COMMIT=$(git rev-parse --short HEAD) docker compose --profile tools run --build --rm related-signals-evaluate
```

São gerados em `data/reports/`:

- `related-signals-evaluation.json`, para auditoria técnica;
- `related-signals-evaluation-health.md`, para apresentação à equipe de saúde.

### Amostra controlada com OpenAI

A execução ao vivo usa a amostra sintética versionada `relation-calibration-v3`, sem dados pessoais.
Com o padrão de um caso por tipo de relação, há 25 pares possíveis e cinco relações conhecidas. A
seleção barata de candidatos ocorre antes da IA; somente os pares selecionados geram chamadas.

```bash
docker compose --profile live run --build --rm related-signals-evaluate-openai
```

O resultado fica em `data/reports/related-signals-live-quality.json`. A quantidade real de chamadas,
tokens de entrada e saída, latência e custo estimado é registrada no próprio resultado. O comando
usa `OPENAI_API_KEY` do ambiente sem imprimir a chave.

Na execução controlada de 08/11/2026, a seleção enviou quatro pares ao modelo. Foram contabilizados
2.214 tokens de entrada, 289 de saída e custo estimado de US$ 0,00036590. Não ocorreram falhas; a
latência do julgamento foi 2.041 ms no p50 e 3.460 ms no p95. Nessa amostra pequena, a cobertura dos
cinco pares relacionados conhecidos e o macro F1 foram 1,00. O resultado é favorável para a prova
de conceito, mas não permite generalização estatística ou sanitária.

Essa execução mede o julgamento do provedor. Os tempos gravados das demais etapas e da leitura da
aba continuam sendo uma fixture de regressão do contrato, e não devem ser apresentados como
benchmark de produção.

O custo é calculado com `OPENAI_INPUT_USD_PER_MILLION` e
`OPENAI_OUTPUT_USD_PER_MILLION`. Esses valores precisam acompanhar o modelo configurado, porque o
provedor pode alterar preços. A Responses API informa tokens de entrada, saída e total; a adaptação
atual registra entrada e saída. Como o detalhamento de tokens em cache ainda não é persistido, a
estimativa trata toda entrada cobrada como não cacheada, uma aproximação conservadora.

## Falhas e recuperação

Os cenários obrigatórios são backlog (`pending`), timeout (`failed`), limite de requisições
(`failed`), cota esgotada (`failed`) e reprocessamento (`ready` ao concluir). A versão do prompt e a
versão da ficha participam da chave de cache, impedindo que uma mudança reutilize silenciosamente
uma sugestão antiga.

Uma execução que não alcance qualquer limite recebe `block`. Antes de uma demonstração, a regressão
deve ser corrigida ou registrada em issue específica; o relatório não pode ser promovido como
aprovação. Uma fixture aprovada recebe `approve_with_caveats`; somente uma medição ao vivo pode
fornecer evidência do provedor, ainda restrita ao escopo técnico e sintético.

## Fontes do método de contabilização

- [Responses API — criação e campo `usage`](https://developers.openai.com/api/reference/resources/responses/methods/create)
- [Preços da API](https://developers.openai.com/api/docs/pricing)
- [Contagem de tokens](https://developers.openai.com/api/docs/guides/token-counting)
- [Prompt caching](https://developers.openai.com/api/docs/guides/prompt-caching)

