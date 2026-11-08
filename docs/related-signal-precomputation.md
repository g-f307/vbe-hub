---
id: DES-003
type: design
status: active
title: Pré-cálculo assíncrono de sinais relacionados
created: 2026-11-08
updated: 2026-11-08
owner: VBE Hub
implemented_code:
  - backend/src/vbe_hub/related_worker/
  - backend/src/vbe_hub/application/correlation/precompute.py
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

Sem `OPENAI_API_KEY`, o worker permanece ocioso e API, frontend e dados previamente persistidos
continuam disponíveis. Gemini não faz parte desse caminho. Suas configurações e adapters antigos
permanecem apenas porque as avaliações históricas ainda são reproduzíveis.

## Integração e validação

O caso de uso que materializa um novo sinal deve chamar `RelatedSignalQueue.enqueue(signal.id)`
depois que a transação do sinal for confirmada. A API pública de detecção será conectada a esse
ponto na issue #71; até lá, o contrato e o consumidor estão prontos, mas não existe endpoint novo.

Validação sem consumir API real:

```bash
docker compose --profile tools run --rm unit-test
docker compose --profile tools run --rm integration-test
docker compose --profile tools run --rm lint
```

Os testes usam doubles nas fronteiras OpenAI e cobrem deduplicação/capacidade da fila, limite de
candidatos, falha sem bloqueio, dimensão inválida, tamanho de entrada, persistência e cache.
