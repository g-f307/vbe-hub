---
id: API-009
type: api
status: active
title: API versionada de sinais individuais e fichas
created: 2026-11-08
updated: 2026-11-08
owner: VBE Hub
implemented_code:
  - backend/src/vbe_hub/api/individual_signals.py
related_docs:
  - ADR-010
  - API-008
  - DATA-002
  - DES-003
---

# API versionada de sinais individuais e fichas

## Resultado e limite

Os endpoints `/v1` entregam o contrato do novo fluxo sem retirar `/signals`, ainda usado pelo
frontend legado. Um sinal representa exatamente uma notícia ou relato comunitário. A resposta
preserva texto, ficha técnica e proveniência de cada fonte; não cria resumo destrutivo e não expõe
`original_payload`, credenciais ou configurações internas.

Condição, relação e confiança produzidas por IA são sugestões auditáveis. A decisão de colocar
sinais na mesma ficha é sempre um comando explícito do analista. Autenticação institucional está
fora da PoC; `REVIEW_ACTOR_ID` identifica somente o ator demonstrativo registrado no histórico.

## Endpoints

| Método e caminho | Finalidade |
| --- | --- |
| `GET /v1/signals` | Lista um sinal/fonte por card. |
| `GET /v1/signals/{signal_id}` | Retorna fonte imutável, proveniência e última ficha técnica válida. |
| `GET /v1/signals/{signal_id}/related` | Lê sugestões já calculadas, sem chamar a OpenAI. |
| `POST /v1/investigations` | Cria uma ficha com o primeiro sinal. |
| `GET /v1/investigations/{file_id}` | Retorna membros individualizados e histórico. |
| `POST /v1/investigations/{file_id}/members/{signal_id}` | Adiciona um sinal por decisão humana. |
| `POST /v1/investigations/{file_id}/members/{signal_id}/removals` | Remove o vínculo por novo evento auditável. |

O OpenAPI navegável permanece em `/docs` e contém os schemas completos.

## Paginação e estados

As coleções usam cursor opaco e ordenação determinística, em vez de `offset`. `limit` aceita de 1
a 100 itens e vale 25 por padrão. Envie `next_cursor` como `cursor` na chamada seguinte. Cursor
inválido retorna `422` com `invalid_cursor`.

`GET /v1/signals` aceita `state` e `source_kind`. Nesta etapa, um sinal sem ficha ativa é
`detected`; após inclusão humana, é `triage`. Os demais estados já fazem parte do contrato, mas a
persistência de suas transições será entregue pelo workflow individual da issue #72; até lá, seus
filtros retornam coleção vazia em vez de inferir decisões.

`GET /related` aceita `suggestion_status=pending|ready|failed`. Cada item informa o estado do
processamento, candidato e data. Em `ready`, pode informar relação, justificativa e confiança; em
`failed`, informa código sanitizado. Abrir a aba nunca chama provedor externo.

## Escritas humanas

Toda escrita exige `operation_key` de 1 a 128 caracteres. Repetir a mesma chave com o mesmo
comando devolve o resultado já registrado, sem duplicar membro ou evento. Reutilizá-la para outro
comando retorna `409 operation_key_conflict`.

Adicionar ou remover membro exige `expected_version`. Versão antiga retorna
`409 investigation_version_conflict` com versões esperada e atual. Um sinal não pode pertencer a
duas fichas ativas; o conflito é `signal_already_assigned`. A última fonte de uma ficha não pode
ser removida. Inclusão, atualização de versão e evento são confirmados ou revertidos juntos na
mesma transação PostgreSQL.

Exemplo sanitizado de criação:

```json
{
  "signal_id": "018f6d5d-9c44-7b10-8000-000000000001",
  "operation_key": "triage-session-001"
}
```

## Compatibilidade

`/signals`, seu detalhe, workflow e métricas consolidadas permanecem disponíveis durante a
estratégia expand/contract. Novos consumidores devem usar `/v1`. A retirada do contrato legado
exigirá uma decisão posterior, atualização do frontend e evidência de que nenhum consumidor ainda
depende dele.

## Validação

Os testes cobrem coleção limitada, OpenAPI, detalhe e proveniência, sugestões pendentes e falhas,
criação, repetição, conflito de idempotência, concorrência otimista, remoção por evento e
preservação dos textos individuais:

```bash
docker compose --profile tools run --build --rm integration-test \
  uv run --no-sync pytest tests/integration/api/test_individual_signal_api.py
```

Os dados da PoC são sintéticos e a API não representa validação clínica ou epidemiológica.
