---
id: API-008
type: api
status: active
title: Consulta canônica de sinais para o painel
created: 2026-10-08
updated: 2026-10-10
owner: VBE Hub
implemented_code:
  - backend/src/vbe_hub/api/signals.py
related_docs:
  - API-005
  - API-006
  - API-007
  - DATA-001
  - UI-001
---

# Consulta canônica de sinais para o painel

## Finalidade e limite

Esta API fornece a fila de sinais e o detalhe de investigação a partir do banco persistente da
PoC. Ela existe para que o painel consulte uma representação única, sem ler o PostgreSQL, executar
IA ou montar dados a partir de mocks no navegador.

As respostas organizam evidências sintéticas para revisão. Condição, correlação e prioridade são
sugestões rastreáveis; nenhuma resposta confirma ocorrência, surto, risco ou decisão sanitária.

As telas v0 de triagem e investigação já consomem este contrato, preservando sua aparência e seus
componentes. O panorama ainda é uma demonstração separada com mocks explicitamente identificados.

## Endpoints

| Método e caminho | Finalidade |
| --- | --- |
| `GET /signals` | Retorna página de sinais para a fila de triagem. |
| `GET /signals/{signal_id}` | Retorna investigação, fontes, ficha disponível, relações e auditoria de um sinal. |

`signal_id` é o UUID persistido. Ele é a identidade usada nos links e ações futuras; um código
legível apresentado pela interface não substitui esse identificador.

## Fila de triagem

`GET /signals` aceita os parâmetros abaixo. Campos omitidos não filtram o resultado.

| Parâmetro | Regra |
| --- | --- |
| `page` | Inteiro a partir de 1; padrão 1. |
| `page_size` | Entre 1 e 100; padrão 25. |
| `state` | `detected`, `triage`, `verification`, `risk_assessment` ou `closed`. |
| `priority_band` | `routine`, `attention` ou `prompt`; ausência de prioridade não é incluída quando este filtro é usado. |
| `query` | Busca textual em título, resumo, condição, sintoma e área consolidada. |
| `condition` | Condição ou síndrome consolidada, sem diferenciação de maiúsculas/minúsculas. |
| `municipality`, `district` | Área consolidada exata, sem diferenciação de maiúsculas/minúsculas. |
| `source_kind` | `media` ou `community`; seleciona sinais com ao menos uma evidência daquele tipo. |
| `period_start`, `period_end` | Datas ISO que devem sobrepor o período consolidado. A API rejeita intervalo invertido. |

A resposta contém `items`, `total`, `page` e `page_size`. Cada item inclui:

- identificação, título e resumo determinísticos do sinal;
- condições, sintomas, período e localização consolidada; campos não preservados no agrupamento
  são retornados como `null`, não inferidos;
- contagem de fontes de mídia e comunidade;
- última prioridade disponível, com faixa, score, confiança, política e identidade da sugestão;
- estado, versão e `updated_at` do workflow; antes da primeira decisão, representa `detected`,
  versão `0` e `updated_at: null` sem materializar uma linha de workflow.

A ordenação é determinística: faixa de prioridade sugerida (`prompt`, `attention`, `routine`, sem
prioridade), score, data de criação e UUID. A faixa e o score servem somente à organização da fila.

## Detalhe de investigação

`GET /signals/{signal_id}` devolve:

- `signal`: a mesma leitura rápida da fila;
- `grouping`: identidade e versão da política, estado de processamento e divergências preservadas;
- `sources`: cada registro normalizado que compõe o sinal, seu papel (`core` ou `context`), tipo,
  emissor, data, título, trecho limitado a 500 caracteres e a última ficha técnica bem-sucedida;
- `relations`: relações usadas no agrupamento, com papel, classificação, confiança, justificativa,
  método e estado;
- `audit_events`: eventos append-only já persistidos, em ordem de sequência.

A API não expõe o payload original completo, o gabarito reservado de avaliação, credenciais ou
qualquer campo de configuração sensível. Uma falha mais recente de extração não esconde uma ficha
técnica bem-sucedida já disponível. Quando não há ficha bem-sucedida, o campo retorna `null`.

## Workflow e ausência de efeitos colaterais

Consultas de leitura nunca criam workflow, evento de auditoria ou outra escrita. Se ainda não houver
linha em `signal_workflows`, a resposta representa o estado inicial como `detected`, versão `0` e
histórico vazio. A primeira transição ou revisão explícita continua usando os endpoints descritos em
[revisão humana e trilha de auditoria](human-review-workflow.md).

O sinal inexistente retorna `404` com o código estável `signal_not_found`. Parâmetros incompatíveis
ou fora dos limites recebem `422` pela validação HTTP; intervalo temporal invertido recebe o código
`invalid_period_range`.

## Validação

Os testes de integração exercitam fila vazia, serialização de dados persistidos, proveniência da
fonte, estado inicial sem escrita, filtros por workflow/prioridade/fonte/condição/período e a
preservação da última ficha técnica válida. Execute-os sem runtime instalado no host:

```bash
docker compose --profile tools run --rm integration-test \
  uv run --no-sync pytest tests/integration/api/test_signal_read_api.py
```

Os checks completos continuam descritos em [execução e validação local](development.md).
