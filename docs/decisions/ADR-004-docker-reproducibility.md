---
id: ADR-004
type: adr
status: active
title: "ADR-004: Usar Docker como interface oficial de reprodução"
created: 2026-09-28
updated: 2026-09-28
owner: VBE Hub
related_docs:
  - REQ-001
  - DES-001
  - REL-001
---

# ADR-004: Usar Docker como interface oficial de reprodução

## Status

Aceita em 2026-09-28.

## Contexto

A PoC será avaliada em outros dispositivos e precisa ser reproduzível a partir do repositório. Instalações manuais de Python, Node.js, PostgreSQL, Redis ou extensões de banco aumentariam a variação do ambiente e dificultariam a validação acadêmica.

## Decisão

Docker Compose será a interface oficial para construir, configurar, executar, testar e demonstrar a aplicação. O host precisará apenas de Git, Docker e Docker Compose.

A composição será incremental: API, PostgreSQL/pgvector, Redis e utilitários sintéticos entram na etapa 1; worker e frontend serão adicionados quando seus módulos forem implementados. O caminho oficial de validação deve sempre funcionar sem runtimes da aplicação instalados diretamente no host.

## Alternativas consideradas

- Instalação local documentada: rejeitada como caminho oficial porque amplia diferenças de versão e configuração entre dispositivos.
- Máquina virtual completa: rejeitada pelo custo de distribuição e manutenção para a PoC.
- Kubernetes: rejeitado por acrescentar complexidade operacional sem necessidade demonstrada.
- Docker apenas no final: rejeitado porque problemas de empacotamento apareceriam tarde e poderiam comprometer o prazo de validação.

## Consequências

- Dockerfiles, Compose, migrations, health checks e comandos em contêiner fazem parte da definição de pronto desde a etapa 1.
- A CI precisa construir e executar a composição em ambiente limpo.
- O desenvolvimento pode usar hot reload, mas não pode divergir do caminho de validação.
- Imagens e dependências devem ter versões fixadas.
- A indisponibilidade de uma API externa precisa de fallback explícito para demonstração, sem mascarar que o resultado foi simulado ou pré-gerado.
- A limpeza de volumes será um comando separado e documentado por ser destrutiva.
