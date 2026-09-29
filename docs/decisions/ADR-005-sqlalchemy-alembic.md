---
id: ADR-005
type: adr
status: active
title: "ADR-005: Usar SQLAlchemy e Alembic na persistência PostgreSQL"
created: 2026-09-28
updated: 2026-09-28
owner: VBE Hub
related_docs:
  - DES-001
  - DATA-001
  - ADR-001
  - ADR-004
---

# ADR-005: Usar SQLAlchemy e Alembic na persistência PostgreSQL

## Status

Aceita em 2026-09-28.

## Contexto

O projeto precisa de acesso assíncrono ao PostgreSQL, mapeamentos fora do domínio, JSONB, restrições explícitas e migrations reversíveis executáveis pela imagem da aplicação. A persistência deve continuar substituível sem contaminar entidades e casos de uso.

## Decisão

Usar SQLAlchemy 2.x com driver asyncpg nos adapters e Alembic para migrations. Entidades de domínio permanecem dataclasses sem decorators ou classes-base do ORM. A migration é a fonte de verdade operacional do schema; o metadata é comparado com ela por `alembic check`.

## Alternativas consideradas

- asyncpg direto: menor abstração, mas exigiria manter manualmente mapeamento, unidade de trabalho e ferramentas de evolução do schema.
- SQLModel: reduz código em APIs simples, porém aproxima modelos de validação, domínio e persistência, contrariando a separação adotada.
- migrations SQL manuais: oferecem controle total, mas aumentam o custo de histórico, downgrade e detecção de divergências nesta equipe pequena.

## Consequências

- O domínio não importa SQLAlchemy ou Alembic.
- Repositórios fazem conversão explícita entre modelos persistentes e entidades.
- Toda alteração estrutural requer migration revisável e reversível.
- O Compose executa migrations antes de iniciar a API.
- Testes de integração usam PostgreSQL/pgvector real; testes do domínio permanecem independentes do banco.
