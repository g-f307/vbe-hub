---
id: ADR-001
type: adr
status: active
title: "ADR-001: Adotar monólito modular para a PoC"
created: 2026-09-28
updated: 2026-09-28
owner: VBE Hub
related_docs:
  - DES-001
---

# ADR-001: Adotar monólito modular para a PoC

## Status

Aceita em 2026-09-28.

## Contexto

A validação tem prazo curto e será executada com dados sintéticos, mas precisa preservar extensibilidade para conectores, IA e painel.

## Decisão

Implementar uma aplicação única com módulos de domínio, processamento, persistência e adapters independentes.

## Alternativas consideradas

- Microserviços: aumentariam deploy, observabilidade e comunicação sem benefício comprovado nesta etapa.
- Script único: seria rápido inicialmente, mas não preservaria fronteiras nem rastreabilidade suficientes.

## Consequências

O sistema será simples de executar localmente e poderá separar serviços no futuro se volume ou equipes justificarem a mudança.
