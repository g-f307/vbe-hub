---
id: API-005
type: api
status: active
title: Indexação semântica
created: 2026-09-30
updated: 2026-09-30
owner: VBE Hub
implemented_code:
  - backend/src/vbe_hub/application/ai/embeddings.py
  - backend/src/vbe_hub/adapters/ai/gemini_embeddings.py
  - backend/src/vbe_hub/adapters/persistence/embedding_repository.py
related_docs:
  - API-003
  - API-004
  - DATA-001
  - ADR-002
---

# Indexação semântica

Esta etapa reduz o universo de pares que seguirá para o julgamento de relação. Ela não decide
se dois sinais pertencem ao mesmo evento e não atribui prioridade sanitária.

## Representação indexada

`embedding-text-v1` monta um texto determinístico somente com os campos semânticos da ficha:
doença/agravo, patógeno, síndrome, sintomas, estimativas de casos e óbitos, grupo afetado,
ambiente, período e localização. Confiança e evidências de auditoria não entram no vetor.

O contrato inicial usa `gemini-embedding-2`, tarefa `RETRIEVAL_DOCUMENT` e 768 dimensões. O
adapter impõe limite de entrada, timeout e nenhuma repetição interna do SDK. Uma resposta com
quantidade inesperada de vetores, dimensão incorreta ou valores inválidos falha de forma fechada
e expõe somente uma mensagem sanitizada.

## Persistência e compatibilidade

A tabela `record_embeddings` preserva o vínculo com `normalized_records` e registra o hash da
entrada, provedor, modelo, versão da representação, dimensionalidade e data de criação. A chave
única composta permite reprocessar atomicamente a mesma versão sem duplicar o registro.

A consulta por distância de cosseno filtra no banco por provedor, modelo, versão da representação
e dimensão, exclui o próprio registro e retorna os resultados em ordem decrescente de similaridade.
Assim, vetores de contratos incompatíveis nunca são comparados. Um índice HNSW com
`vector_cosine_ops` atende a recuperação aproximada em volume; em tabelas pequenas, o PostgreSQL
pode corretamente preferir uma varredura sequencial.

Embeddings recebem a mesma classificação de sensibilidade dos dados que os originaram. Nesta
PoC, somente fichas produzidas de dados sintéticos são elegíveis. O vínculo com a origem deve ser
preservado e uma futura separação por organização terá de ser aplicada também na indexação e na
consulta, antes do uso com dados reais.

## Validação reproduzível

```bash
docker compose build test migrate
docker compose run --rm test uv run --no-sync pytest \
  tests/unit/application/ai/test_embedding_text.py \
  tests/unit/application/ai/test_embedding_service.py \
  tests/unit/adapters/ai/test_gemini_embeddings.py \
  tests/integration/persistence/test_embedding_repository.py
```

Os testes cobrem a representação estável, o contrato do adapter, persistência, reprocessamento,
ordenação por similaridade e isolamento entre versões de modelo.

[Voltar ao índice da documentação](README.md)
