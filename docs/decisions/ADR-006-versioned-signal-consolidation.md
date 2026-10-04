---
id: ADR-006
type: adr
status: active
title: "ADR-006: Consolidar sinais com política determinística e versionada"
created: 2026-10-02
updated: 2026-10-02
owner: VBE Hub
related_docs:
  - API-004
  - API-005
  - DATA-001
---

# ADR-006: Consolidar sinais com política determinística e versionada

## Status

Aceita em 2026-10-02.

## Contexto

Relações classificadas por IA precisam ser transformadas em unidades revisáveis sem apagar as
fontes, transformar contexto fraco em confirmação ou tornar o resultado dependente da ordem de
execução. Mudanças futuras nas regras também não podem reinterpretar silenciosamente resultados
anteriores.

## Decisão

Usar componentes determinísticos formados apenas por relações fortes (`duplicate`,
`corroborates` e `updates`). Antes de cada união, comparar todos os pares entre os componentes e
bloquear conflitos geográficos, clínicos ou temporais fortes. Tratar `related_context` como vínculo
de contexto incapaz de unir dois componentes já estabelecidos.

Persistir membros e avaliações de relação como vínculos explícitos. Calcular a identidade do sinal
com a versão da política e os membros ordenados, permitindo reprocessamento idempotente e
coexistência de versões.

## Alternativas consideradas

- Agrupar por transitividade de qualquer relação positiva: simples, mas uma evidência contextual
  fraca poderia unir ocorrências distintas.
- Permitir que a IA gere diretamente o sinal final: reduziria código, porém dificultaria
  reprodutibilidade, proveniência e explicação dos conflitos.
- Sobrescrever sinais quando a política mudar: economizaria armazenamento, mas eliminaria a
  comparação e a auditoria histórica.

## Consequências

- A consolidação é reprodutível e testável sem chamar um provedor externo.
- Todo campo derivado e toda relação aceita continuam rastreáveis até suas origens.
- Divergências e uniões rejeitadas permanecem disponíveis para inspeção.
- Uma alteração de regra exige nova versão de política e pode coexistir com resultados antigos.
- Decisão sanitária, prioridade e correções humanas permanecem fora deste caso de uso.

