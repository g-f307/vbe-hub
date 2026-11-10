---
id: ADR-011
type: adr
status: active
title: "ADR-011: Centralizar a investigação em um sinal-cabeça e preservar evidências"
created: 2026-11-10
updated: 2026-11-10
owner: VBE Hub
related_docs:
  - ADR-008
  - ADR-010
  - API-009
  - DATA-002
  - UI-001
---

# ADR-011: Centralizar a investigação em um sinal-cabeça e preservar evidências

## Status

Aceita em 2026-11-10 e implementada na issue #89. Substitui na ADR-010 somente a decisão de que o
sinal que inicia a composição não teria privilégio persistente. Permanecem válidas a unidade
individual por fonte, a sugestão assíncrona da IA, a decisão humana e a auditoria append-only.

## Contexto

A ficha simétrica da ADR-010 preservava as fontes, mas não oferecia um ponto operacional estável.
Após relacionar dois sinais, ambos desapareciam da fila e a interface apresentava os membros como
equivalentes, inclusive com mensagens ambíguas sobre pertencer a outra ficha. Isso dificultava
explicar qual investigação o analista estava conduzindo e onde consultar ou corrigir evidências.

## Decisão

Toda ficha possui exatamente um `head_signal_id`, definido pelo sinal a partir do qual o analista
confirma a composição. A cabeça permanece como item navegável da fila e não pode ser removida da
própria ficha. Os demais membros ativos são evidências: deixam a fila individual, não reaparecem
como candidatos e continuam preservados para leitura e auditoria dentro da cabeça.

A ficha técnica apresentada é uma projeção de leitura. Valores ausentes na cabeça podem ser
complementados por evidências; listas recebem itens novos. Valores escalares divergentes não são
sobrescritos: a cabeça é mantida e a alternativa é registrada como conflito com o sinal de origem.
Textos, extrações e proveniência originais nunca são modificados.

Remover uma evidência cria evento corretivo, preserva o histórico e devolve o sinal à sua fila
individual em triagem. A IA continua somente pré-calculando candidatos; abrir qualquer aba não
chama o provedor e nenhuma sugestão cria vínculo automaticamente.

## Alternativas consideradas

### Manter todos os membros simétricos

Rejeitada porque não produz um endereço operacional estável nem explica por que todos os cards
somem depois da composição.

### Copiar campos das evidências para a extração da cabeça

Rejeitada porque destruiria a separação entre dado original e projeção, enfraqueceria a
proveniência e tornaria a remoção difícil de reverter.

### Escolher a cabeça pelo maior score da IA

Rejeitada porque converteria sugestão técnica em decisão operacional. A cabeça deriva do contexto
explícito da ação humana.

## Consequências

- `investigation_files` passa a persistir uma cabeça imutável com FK e unicidade.
- Fichas históricas recebem como cabeça o primeiro membro ativo, única aproximação determinística
  disponível; a ordem e os eventos anteriores permanecem consultáveis.
- A fila lista sinais livres e cabeças, enquanto relacionados exclui qualquer membro ativo.
- A API da ficha expõe cabeça, projeção técnica, proveniência por campo e conflitos.
- A interface separa análise, candidatos inéditos e gerenciamento de evidências.
- Consultas que precisem contar fontes devem usar membros; contar investigações deve usar cabeças
  ou fichas, sem somar as duas unidades.

## Limites

A projeção não confirma diagnóstico nem resolve divergências epidemiológicas. Autenticação,
autorização institucional e políticas para dados reais continuam fora da PoC.
