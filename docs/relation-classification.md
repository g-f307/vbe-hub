---
id: API-007
type: api
status: active
title: Classificação das relações
created: 2026-09-30
updated: 2026-09-30
owner: VBE Hub
implemented_code:
  - backend/src/vbe_hub/application/correlation/relations.py
  - backend/src/vbe_hub/adapters/ai/gemini_relations.py
  - backend/src/vbe_hub/adapters/persistence/relation_repository.py
related_docs:
  - API-003
  - API-004
  - API-006
  - ADR-002
---

# Classificação das relações

A classificação transforma um par candidato em sugestão auditável. Ela não confirma evento,
surto ou prioridade e permanece sujeita à revisão humana.

## Contrato

O enum `relation-v1` contém `duplicate`, `corroborates`, `updates`, `related_context` e
`unrelated`. Resultado válido inclui justificativa de 1–500 caracteres, confiança finita entre
zero e um e metadados de provider/modelo/versões. Para `updates`, o serviço deriva e registra o
registro temporalmente posterior; datas iguais ou ausentes não permitem essa relação.

O par é canonicalizado pelo UUID, portanto inverter esquerda/direita reutiliza a mesma chave. A
chave inclui `relation-rules-v1` e `relate-v1`. Fichas semanticamente idênticas, desconsiderando
confiança/evidência, usam regra determinística de duplicata. Demais pares seguem para a porta
`RelationJudge`.

## Gemini e conteúdo não confiável

O adapter envia somente as duas fichas, delimitadas como dados não confiáveis, sem gold e sem
ferramentas. A saída usa JSON Schema fechado e é validada localmente. Entrada e saída são
limitadas; falha do SDK ou resposta inválida vira erro sanitizado e nunca relação positiva.

## Persistência

`relation_assessments` guarda o par, relação, método, confiança, justificativa, direção de update,
versões, metadados operacionais e falha sanitizada. O upsert por chave mantém reprocessamento
idempotente. FKs preservam a origem e remoção do registro elimina suas avaliações.

## Validação

```bash
docker compose run --rm unit-test
docker compose run --rm integration-test
```

Os testes cobrem regra de duplicata, uso do provider, direção de atualização, cache canônico,
falha sem relação positiva, fencing e validação estruturada do Gemini.

[Voltar ao índice da documentação](README.md)
