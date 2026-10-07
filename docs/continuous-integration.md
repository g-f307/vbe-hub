---
id: OPS-002
type: operations
status: active
title: Integração contínua
created: 2026-09-29
updated: 2026-10-07
owner: VBE Hub
related_docs:
  - OPS-001
  - ADR-004
---

# Integração contínua

O workflow `.github/workflows/ci.yml` valida pull requests destinados à `main` e todo push na
`main`. A execução usa apenas Docker e Docker Compose para os runtimes da aplicação.

## Checks

| Check | Responsabilidade | Equivalente local principal |
| --- | --- | --- |
| `docs` | Testar o auditor e verificar links e metadados | `docker compose --profile tools run --rm docs-check` |
| `quality` | Executar o Ruff | `docker compose --profile tools run --rm lint` |
| `unit-tests` | Executar testes sem PostgreSQL ou Redis | `docker compose --profile tools run --rm --no-deps unit-test` |
| `frontend` | Executar lint e testes do painel isoladamente | `frontend-lint` e `frontend-test` no profile `tools` |
| `integration-tests` | Aplicar migrations e testar PostgreSQL/pgvector e Redis | `docker compose --profile tools run --rm integration-test` |
| `synthetic-data-validation` | Gerar e validar o lote determinístico | serviços `synthetic-generate` e `synthetic-validate` |
| `docker-smoke` | Reproduzir o caminho completo em ambiente limpo | sequência descrita em [execução local](development.md#smoke-test-reproduzível) |

`docs`, `quality`, `unit-tests`, `frontend` e `integration-tests` podem iniciar em paralelo. A
validação sintética depende da integração, e o smoke test depende de todos os checks anteriores.
Além da API, ele constrói o painel, aguarda seu health check e consulta `/api/health`. Uma nova
execução da mesma referência cancela a anterior.

## Isolamento e segurança

- O `GITHUB_TOKEN` possui apenas permissão de leitura de conteúdo.
- Actions de terceiros são referenciadas por SHA imutável.
- Cada job possui timeout e um escopo próprio de cache Buildx.
- A CI cria `.env` somente a partir de `.env.example`; não usa chaves Gemini nem credenciais
  externas.
- Em falha, somente logs operacionais de PostgreSQL, Redis, migration, API e painel são exibidos. Datasets,
  relatórios com conteúdo e arquivos `.env` não são publicados como artefatos.
- Cada job que inicia serviços remove ao final os volumes efêmeros do runner.

## Proteção prevista para `main`

Depois que os nomes acima estiverem confirmados por uma execução verde, a proteção da `main` deve
exigir pull request, resolução de conversas e os sete checks. Force push e exclusão devem permanecer
bloqueados. Como o repositório é individual, aprovação externa obrigatória não é requisito nesta
etapa.
