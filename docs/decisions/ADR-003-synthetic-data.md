---
id: ADR-003
type: adr
status: active
title: "ADR-003: Validar inicialmente com dados sintéticos rotulados"
created: 2026-09-28
updated: 2026-09-28
owner: VBE Hub
related_docs:
  - DES-001
  - API-001
---

# ADR-003: Validar inicialmente com dados sintéticos rotulados

## Status

Aceita em 2026-09-28.

## Contexto

As APIs reais do EIOS e Guardiões da Saúde não serão usadas na validação atual. Seus formatos, permissões e limites ainda exigem confirmação antes da integração.

## Decisão

Gerar lotes sintéticos de mídia e comunidade, determinísticos e rotulados com evento de referência. O formato segue o contrato em [dados sintéticos](../synthetic-data-contract.md), sem alegar equivalência exata a endpoints reais.

## Alternativas consideradas

- Esperar o acesso às APIs: colocaria o prazo de validação em risco.
- Usar relatos reais públicos: aumentaria obrigações de privacidade, licença e anonimização.

## Consequências

As métricas de correlação serão reproduzíveis. Um conector futuro deverá adaptar o dado real ao envelope comum e ser validado separadamente.
