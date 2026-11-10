---
id: DES-003
type: design
status: active
title: Pré-cálculo assíncrono de sinais relacionados
created: 2026-11-08
updated: 2026-11-09
owner: VBE Hub
implemented_code:
  - backend/src/vbe_hub/related_worker/
  - backend/src/vbe_hub/application/correlation/precompute.py
  - backend/src/vbe_hub/application/correlation/detection.py
  - backend/src/vbe_hub/infrastructure/related_queue.py
  - backend/src/vbe_hub/adapters/persistence/related_signal_repository.py
related_docs:
  - ADR-010
  - API-003
  - API-005
  - API-006
  - DES-002
---

# Pré-cálculo assíncrono de sinais relacionados

Voltar ao [índice da documentação](README.md).

## Resultado entregue

O serviço `relation-worker` prepara sugestões antes da interação do analista. Abrir uma tela não
faz chamada à OpenAI. O produtor agenda somente o UUID do sinal em Redis; a fila possui capacidade
máxima, deduplicação enquanto o trabalho está ativo e no máximo três tentativas por padrão.

O worker executa, nesta ordem:

1. lê o sinal individual e seu registro normalizado preservando a proveniência;
2. extrai uma ficha técnica estruturada ou reutiliza a extração persistida;
3. gera ou atualiza o embedding OpenAI de 768 dimensões;
4. recupera até `RELATED_NEIGHBOR_LIMIT` vizinhos compatíveis pelo índice HNSW;
5. aplica filtros clínico, temporal e territorial determinísticos;
6. envia no máximo `RELATED_CANDIDATE_LIMIT` pares ao julgamento OpenAI;
7. persiste cada sugestão como `pending`, `ready` ou `failed`.

Uma sugestão pronta referencia `relation_assessments`, onde ficam classificação, justificativa,
confiança, provedor, modelo, prompt, consumo, latência, cache e falha sanitizada. A classificação é
apoio auditável: ela não adiciona o sinal à ficha e não confirma diagnóstico, surto ou prioridade.

## Limites e segurança

- `OPENAI_API_KEY` existe apenas no ambiente do backend e nunca é enviada ao frontend;
- texto de notícia e relato é conteúdo não confiável, cercado no prompt e sem ferramentas;
- respostas usam schema estruturado e validação local;
- entrada, saída, timeout, tentativas, tamanho da fila, vizinhos e candidatos possuem teto;
- falha do provedor deixa a sugestão em `failed`, mas não altera nem bloqueia o sinal individual;
- avaliações falhas não são tratadas como cache positivo; uma tentativa posterior pode substituir
  a mesma chave, mantendo o registro auditável atual;
- embeddings recebem a mesma classificação de sensibilidade das fontes que os originaram.

## Configuração

| Variável | Padrão | Função |
| --- | ---: | --- |
| `OPENAI_MODEL` | `gpt-6-luna` | extração e julgamento de relação |
| `OPENAI_EMBEDDING_MODEL` | `text-embedding-3-small` | indexação semântica |
| `OPENAI_TIMEOUT_SECONDS` | `15` | timeout por chamada |
| `OPENAI_MAX_ATTEMPTS` | `3` | tentativas controladas |
| `RELATED_QUEUE_CAPACITY` | `1000` | trabalhos pendentes na fila |
| `RELATED_NEIGHBOR_LIMIT` | `20` | vizinhos consultados no índice |
| `RELATED_CANDIDATE_LIMIT` | `3` | pares enviados ao modelo por sinal |
| `RELATED_MINIMUM_SEMANTIC_SCORE` | `0.65` | piso de similaridade semântica para considerar o par |
| `RELATED_MINIMUM_TOTAL_SCORE` | `0.55` | piso agregado após evidências clínica, temporal e territorial |

O piso agregado é menor que o semântico de propósito: fichas esparsas podem expressar sintomas
equivalentes com palavras diferentes. Um par ainda precisa superar a similaridade semântica de
`0.65`; o piso de `0.55` apenas evita que a ausência de datas, localização estruturada ou igualdade
lexical impeça o julgamento do modelo. O limite de três candidatos e a decisão humana posterior
continuam obrigatórios.

Sem `OPENAI_API_KEY`, o worker permanece ocioso e API, frontend e dados previamente persistidos
continuam disponíveis. Gemini não faz parte desse caminho. Suas configurações e adapters antigos
permanecem apenas porque as avaliações históricas ainda são reproduzíveis.

## Integração e validação

`IndividualSignalDetectionService` materializa idempotentemente um sinal e agenda seu UUID na fila.
A [API versionada](individual-signal-api.md) lê os resultados persistidos sem chamar o provedor;
a conexão do caso de uso aos futuros adaptadores de ingestão permanece separada da leitura HTTP.

Validação sem consumir API real:

```bash
docker compose --profile tools run --rm unit-test
docker compose --profile tools run --rm integration-test
docker compose --profile tools run --rm lint
```

Os testes usam doubles nas fronteiras OpenAI e cobrem deduplicação/capacidade da fila, limite de
candidatos, falha sem bloqueio, dimensão inválida, tamanho de entrada, persistência e cache.
