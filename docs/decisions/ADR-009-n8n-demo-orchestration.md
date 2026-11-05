---
id: ADR-009
type: adr
status: active
title: "ADR-009: Restringir o n8n à orquestração demonstrativa"
created: 2026-11-04
updated: 2026-11-04
owner: VBE Hub
related_docs:
  - ADR-001
  - ADR-004
  - DEMO-001
---

# ADR-009: Restringir o n8n à orquestração demonstrativa

## Status

Aceita em 04/11/2026.

## Contexto

A apresentação da PoC precisa tornar compreensível para profissionais de saúde como fontes
dispersas chegam ao VBE Hub e originam sinais revisáveis. Comandos de terminal não expressam bem
esse percurso. Ao mesmo tempo, duplicar regras de domínio em uma ferramenta visual prejudicaria a
auditabilidade e criaria um segundo backend.

## Decisão

Usar n8n somente como camada visual e orquestradora de uma demonstração local. O workflow representa
as fontes de mídia e comunidade e chama uma rota interna, restrita a cenários sintéticos conhecidos.
O backend permanece responsável por persistência, normalização, extração, relação, consolidação e
prioridade. O perfil `demo` do Docker Compose importa o workflow versionado e mantém os dados do n8n
em volume próprio.

O modo offline é o padrão reproduzível. O modo OpenAI é opcional, recebe a credencial exclusivamente
no backend e limita a entrada aos dois registros sintéticos do cenário. A classificação de relação
dos cenários é congelada para assegurar uma narrativa repetível e não deve ser apresentada como
avaliação de acurácia.

## Alternativas consideradas

- Demonstrar somente por comandos: rejeitado porque oculta a diversidade das fontes e dificulta a
  comunicação com o público não técnico.
- Implementar processamento e regras dentro do n8n: rejeitado porque duplicaria o domínio e a
  persistência canônica.
- Conectar serviços reais de EIOS e Guardiões da Saúde: adiado porque permanece fora do escopo da
  PoC atual e exigiria contratos e autorizações ainda indisponíveis.

## Consequências

- O fluxo visual pode ser reproduzido integralmente por Docker Compose.
- Uma rodada isolada permite comparar fila vazia e cards posteriores sem apagar o banco normal.
- Alterações no contrato da rota demonstrativa e no workflow precisam permanecer sincronizadas.
- n8n não passa a ser requisito da execução básica nem componente de decisão sanitária.
