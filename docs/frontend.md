---
id: UI-001
type: design
status: active
title: Fundação do frontend
created: 2026-10-07
updated: 2026-10-07
owner: VBE Hub
related_docs:
  - DES-001
  - OPS-001
  - OPS-002
  - REL-001
---

# Fundação do frontend

## Propósito e limite atual

`frontend/` contém o painel versionado do VBE Hub, construído em Next.js/React a partir da
exportação do protótipo v0. A fundação torna a interface reproduzível por Docker Compose e preserva
a linguagem visual, navegação responsiva e componentes de evidência enquanto lê dados persistidos.

As rotas atuais são deliberadamente demonstrativas:

| Rota | Papel na fundação | Estado de dados |
| --- | --- | --- |
| `/triagem` | fila, filtros, indicadores e paginação | consulta `GET /signals` no servidor Next |
| `/sinais/[slug]` | ficha técnica, fontes, relações e auditoria | consulta `GET /signals/{id}` no servidor Next; o segmento é o UUID canônico |
| `/panorama` | contexto territorial e indicadores do protótipo | usa mocks versionados; não consulta a API |
| `/api/health` | health check do contêiner do painel | retorna somente o estado do serviço |

Os dados de `lib/mock-data.ts` permanecem exclusivos do panorama, ainda não integrado. Eles não
alimentam triagem ou investigação, não representam situação epidemiológica e não implicam decisão
humana.

## Princípios de apresentação

- O painel usa a marcação visível de ambiente de demonstração. Os sinais, doenças, prioridades e
  decisões exibidos nesta fase são mocks explícitos, não resultados da API.
- A IA continuará sendo apresentada como sugestão auditável. A revisão, justificativa e decisão
  pertencem ao profissional de vigilância.
- A futura fila usa divulgação progressiva: código, estado, condição, local/período e composição de
  fontes ficam no item compacto; evidências, divergências, ficha e auditoria ficam no detalhe.
- A futura visão territorial mostra apenas agregados aprovados por área. Relatos individuais,
  endereço e coordenadas precisas não pertencem ao mapa.

## Fronteira com a API

`lib/signal-read.ts` é a fronteira única de leitura. Ela separa tipos de transporte e apresentação,
valida a resposta mínima, aplica timeout e distingue indisponibilidade, resposta inválida e sinal
inexistente. `VBE_API_INTERNAL_URL` é lida somente no servidor Next e usa `http://api:8000` no
Compose; não há URL interna ou segredo em variável `NEXT_PUBLIC`.

O frontend não acessa PostgreSQL, Redis, provedores de IA ou conectores diretamente. A API já
oferece `GET /signals` e `GET /signals/{signal_id}` para fila e investigação, conforme o [contrato
de leitura](signal-read-api.md). Filtros e paginação são serializados nos parâmetros canônicos da
URL compartilhável. Carregamento, vazio, falha e 404 não usam mocks como fallback. Revisão e
agregados territoriais continuam previstos na [arquitetura](architecture.md#contratos-de-integração-previstos).

## Execução e verificação

Somente Git, Docker e Docker Compose v2 são necessários no host:

```bash
cp .env.example .env
docker compose up --build --detach --wait
```

Abra `http://localhost:3000`. Para verificar isoladamente a fundação no mesmo ambiente que a CI:

```bash
docker compose --profile tools run --rm frontend-lint
docker compose --profile tools run --rm frontend-test
```

O modo de desenvolvimento é opcional e usa recarga automática sem Node.js instalado no host:

```bash
docker compose -f compose.yaml -f compose.dev.yaml up --build
```

Os detalhes de portas, volumes, reconstrução e reset estão em [execução local](development.md).
