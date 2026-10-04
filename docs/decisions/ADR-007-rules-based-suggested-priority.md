---
id: ADR-007
type: adr
status: active
title: "ADR-007: Calcular prioridade sugerida com regras versionadas"
created: 2026-10-03
updated: 2026-10-03
owner: VBE Hub
related_docs:
  - API-005
  - API-006
  - DATA-001
---

# ADR-007: Calcular prioridade sugerida com regras versionadas

## Status

Aceita em 2026-10-03.

## Contexto

O painel precisará ordenar sinais para triagem, mas um número opaco pode ser confundido com risco
epidemiológico definitivo. Dados incompletos também não podem ser convertidos em ausência de
gravidade ou magnitude.

## Decisão

Calcular uma prioridade sugerida por fórmula determinística, com pesos, limites, listas de sinais
graves e versão centralizados. Cada componente mantém fatos e origens. Componentes clínicos
desconhecidos ficam fora da normalização, enquanto completude, confiança e lacunas tornam essa
incerteza visível.

Persistir cada cálculo como histórico imutável ligado à identidade e à versão exatas do sinal. A
identidade inclui o hash integral da configuração. Avaliações humanas usarão contrato e persistência
separados.

## Alternativas consideradas

- Pedir um score ao LLM: rejeitado por reduzir reprodutibilidade e explicabilidade.
- Tratar ausências como zero: rejeitado porque ausência de campo não demonstra ausência de risco.
- Armazenar somente o último valor: rejeitado porque apagaria a política e as evidências usadas.
- Misturar sugestão e decisão humana: rejeitado porque confundiria apoio automatizado com autoridade
  sanitária.

## Consequências

- O score pode ser recalculado e explicado sem acesso ao provedor de IA.
- Pesos iniciais são hipóteses técnicas e precisam de validação posterior.
- Mudanças exigem nova versão/configuração e preservam os resultados anteriores.
- O painel poderá ordenar por score sem esconder confiança, lacunas e conflitos.

