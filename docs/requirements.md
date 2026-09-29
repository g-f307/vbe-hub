---
id: REQ-001
type: requirements
status: active
title: Requisitos e escopo
created: 2026-09-28
updated: 2026-09-28
owner: VBE Hub
related_docs:
  - DES-001
  - API-001
  - REL-001
---

# Requisitos e escopo

## Objetivo

Demonstrar uma prova de conceito que recebe registros sintéticos equivalentes, em nível semântico, a notícias de saúde e relatos comunitários; extrai uma ficha técnica; identifica relações entre registros; e apresenta sinais consolidados para revisão humana.

## Dentro do escopo da validação

- Geração em massa de dados sintéticos, com proveniência e rótulos conhecidos.
- Normalização dos formatos de entrada em um registro comum.
- Extração estruturada por IA de doença/síndrome, sintomas, tempo, lugar, magnitude e contexto.
- Correlação de registros como duplicata, corroboração, atualização, contexto relacionado ou sem relação.
- Agrupamento, prioridade sugerida explicável e painel de revisão.
- Métricas de qualidade e de desempenho sobre um conjunto de referência rotulado.

## Fora do escopo da validação

- Consumo de APIs reais do EIOS ou Guardiões da Saúde.
- Diagnóstico, confirmação de surto, notificação oficial ou resposta de saúde pública.
- Armazenamento de dados pessoais, identificáveis ou clínicos individuais.

## Critérios de aceite da macroentrega 1

- Importar um lote sintético reprodutível e processar todos os registros sem intervenção manual.
- Exibir, para cada registro, texto de origem, ficha técnica extraída, confiança e origem sintética.
- Exibir, para cada sinal consolidado, fontes vinculadas, relação entre registros, justificativa, prioridade sugerida e status do fluxo.
- Permitir ao avaliador aceitar, corrigir ou rejeitar a sugestão de relação/agrupamento.
- Gerar relatório com precisão, revocação, F1, falsos positivos e tempo de processamento.

## Fundamentação operacional

O fluxo implementado seguirá a separação proposta pelo Africa CDC: detecção, triagem, verificação, avaliação de risco e alerta/resposta. A PoC automatiza detecção, pré-triagem e sugestão de correlação; verificação e avaliação de risco permanecem humanas.
