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
a linguagem visual, navegação responsiva e componentes de evidência antes de acoplar dados
persistidos.

As rotas atuais são deliberadamente demonstrativas:

| Rota | Papel na fundação | Estado de dados |
| --- | --- | --- |
| `/triagem` | fila, filtros e indicadores do protótipo | usa mocks versionados; não consulta a API |
| `/sinais/[slug]` | ficha técnica, fontes e auditoria do protótipo | usa mocks versionados; não consulta a API |
| `/panorama` | contexto territorial e indicadores do protótipo | usa mocks versionados; não consulta a API |
| `/api/health` | health check do contêiner do painel | retorna somente o estado do serviço |

Os dados de `lib/mock-data.ts` são exclusivos de demonstração e foram mantidos para preservar a
experiência gerada pelo v0. Eles não representam situação epidemiológica, não são enviados ao
backend e não implicam decisão humana.

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

O cliente HTTP começa em `lib/api-client.ts`. Nesta etapa ele somente resolve
`NEXT_PUBLIC_VBE_API_URL`; aceita HTTP(S), remove a barra final e rejeita URL com credenciais,
parâmetros ou fragmentos. A variável é pública por definição, portanto nunca pode receber chave,
token ou qualquer segredo.

O frontend não acessa PostgreSQL, Redis, provedores de IA ou conectores diretamente. As próximas
entregas fornecerão endpoints versionados para fila, ficha, evidências, revisão e agregados
territoriais, conforme a [arquitetura](architecture.md#contratos-de-integração-previstos).

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
