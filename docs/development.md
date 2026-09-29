---
id: OPS-001
type: operations
status: active
title: Execução e validação local
created: 2026-09-28
updated: 2026-09-28
owner: VBE Hub
related_docs:
  - DES-001
  - ADR-004
---

# Execução e validação local

## Pré-requisitos

- Git;
- Docker Engine ou Docker Desktop;
- Docker Compose v2.

Python, uv, PostgreSQL e Redis não precisam ser instalados no host.

## Primeira execução

```bash
cp .env.example .env
docker compose up --build --detach --wait
docker compose ps
```

A API fica disponível em `http://localhost:8000`. A porta pode ser alterada por `API_PORT` no arquivo `.env`. PostgreSQL e Redis permanecem acessíveis apenas na rede interna da composição.

Endpoints operacionais:

- `GET /health/live`: confirma que o processo HTTP está ativo;
- `GET /health/ready`: confirma PostgreSQL, extensão pgvector e Redis; retorna HTTP 503 se qualquer dependência estiver indisponível.

## Verificações oficiais

```bash
docker compose --profile tools run --rm test
docker compose --profile tools run --rm lint
```

O gerador e o importador sintéticos também são ferramentas da composição:

```bash
docker compose --profile tools run --rm synthetic-generate
docker compose --profile tools run --rm synthetic-import
```

Os artefatos massivos ficam em `data/generated/` e não são versionados. Consulte [geração e importação de dados sintéticos](synthetic-data-generation.md) para configuração e verificação dos hashes.

Para reconstruir sem reaproveitar o cache local:

```bash
docker compose build --pull --no-cache
docker compose up --detach --wait
```

O bootstrap cria a extensão `vector` e um usuário não administrador para a aplicação. O schema da aplicação é gerido exclusivamente pelas migrations versionadas.

O serviço `migrate` aplica automaticamente as migrations antes da API. Os comandos abaixo permitem verificar ou operar o histórico sem Alembic instalado no host:

```bash
docker compose run --rm migrate uv run --no-sync alembic current
docker compose run --rm migrate uv run --no-sync alembic upgrade head
docker compose run --rm migrate uv run --no-sync alembic check
```

Downgrade é uma operação de desenvolvimento e pode remover dados. Para testar a reversibilidade da última migration em um banco descartável:

```bash
docker compose run --rm migrate uv run --no-sync alembic downgrade -1
docker compose run --rm migrate uv run --no-sync alembic upgrade head
```

## Desenvolvimento com recarga automática

```bash
docker compose -f compose.yaml -f compose.dev.yaml up --build
```

Esse modo monta somente `backend/src` e `backend/tests`. O fluxo de validação e a CI usam a imagem construída sem esses volumes.

## Persistência e encerramento

`postgres_data` guarda o banco e `redis_data` guarda os snapshots do Redis. O encerramento normal preserva ambos:

```bash
docker compose down
```

O comando abaixo é destrutivo e remove todos os dados locais desses volumes:

```bash
docker compose down --volumes
```

Use o reset apenas quando a perda dos dados locais for intencional. O arquivo `.env` é ignorado pelo Git e não deve conter credenciais reais destinadas ao repositório.

Após um reset, `docker compose up --build --detach --wait` recria o banco, habilita pgvector e reaplica todas as migrations. Backup e restauração não fazem parte desta etapa; os volumes locais não substituem uma política de backup.
