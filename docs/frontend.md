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

`frontend/` contém o painel versionado do VBE Hub, construído em Next.js/React. A fundação torna a
interface reproduzível por Docker Compose e valida a linguagem visual, navegação responsiva,
acessibilidade básica e estados operacionais antes de acoplar dados persistidos.

As rotas atuais são deliberadamente demonstrativas:

| Rota | Papel na fundação | Estado de dados |
| --- | --- | --- |
| `/triagem` | entrada para a futura fila de sinais | não consulta a API |
| `/sinais/[signalId]` | estrutura da futura ficha técnica | não consulta a API |
| `/panorama` | base para o futuro contexto territorial agregado | não consulta a API |
| `/api/health` | health check do contêiner do painel | retorna somente o estado do serviço |

Os parâmetros `?estado=carregando`, `?estado=vazio` e `?estado=indisponivel` tornam verificáveis os
estados de interface. Eles são apenas recursos de demonstração: não representam situação
epidemiológica, não são enviados ao backend e não implicam decisão humana.

## Princípios de apresentação

- O painel usa a marcação visível de ambiente de demonstração e não inventa sinais, doenças,
  prioridades ou decisões quando não há integração de dados.
- A IA continuará sendo apresentada como sugestão auditável. A revisão, justificativa e decisão
  pertencem ao profissional de vigilância.
- A futura fila usa divulgação progressiva: código, estado, condição, local/período e composição de
  fontes ficam no item compacto; evidências, divergências, ficha e auditoria ficam no detalhe.
- A futura visão territorial mostra apenas agregados aprovados por área. Relatos individuais,
  endereço e coordenadas precisas não pertencem ao mapa.

## Fronteira com a API

O cliente HTTP começa em `src/lib/api.ts`. Nesta etapa ele somente resolve
`NEXT_PUBLIC_API_BASE_URL`; aceita HTTP(S), remove a barra final e rejeita URL com credenciais,
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
