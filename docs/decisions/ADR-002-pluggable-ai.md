---
id: ADR-002
type: adr
status: active
title: "ADR-002: Isolar provedores de IA"
created: 2026-09-28
updated: 2026-09-28
owner: VBE Hub
related_docs:
  - DES-001
---

# ADR-002: Isolar provedores de IA

## Status

Aceita em 2026-09-28.

## Contexto

A PoC precisa de extração estruturada, embeddings e julgamento de relações. Gemini oferece saída estruturada e embeddings por API. Ollama pode permitir experimentos locais, mas a GPU de 4 GB limita modelos generativos maiores.

## Decisão

Definir interfaces de domínio para extração, embeddings e julgamento de relação. Usar Gemini como implementação inicial de referência e Ollama somente como implementação opcional de comparação local.

## Alternativas consideradas

- Acoplar todo o domínio a Gemini: reduz o trabalho imediato, mas dificulta teste local e mudança de fornecedor.
- Usar somente Ollama: reduz chamadas externas, mas cria risco de qualidade e latência no hardware disponível.

## Consequências

O código terá pequenos adapters adicionais. Em troca, testes podem usar um provedor falso, e a comparação Gemini/Ollama torna-se uma avaliação empírica do TCC.
