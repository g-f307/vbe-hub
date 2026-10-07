---
id: ADR-008
type: adr
status: active
title: "ADR-008: Registrar decisões humanas como eventos imutáveis"
created: 2026-10-06
updated: 2026-10-06
owner: VBE Hub
related_docs:
  - API-007
  - DATA-001
  - ADR-006
  - ADR-007
---

# ADR-008: Registrar decisões humanas como eventos imutáveis

## Status

Aceita em 2026-10-06.

## Contexto

O VBE Hub precisa distinguir sugestões automáticas de decisões humanas e explicar quem decidiu,
quando, sobre qual versão e a partir de quais valores. Atualizar somente o estado atual apagaria a
sequência da análise; concorrência entre revisores também poderia causar perda silenciosa.

## Decisão

Manter um agregado de fluxo por sinal, com estado e versão otimista, e registrar cada transição ou
revisão como evento imutável. Eventos carregam valor anterior e novo e são protegidos contra
`UPDATE` e `DELETE` no banco. Correções posteriores são novos eventos compensatórios.

Usar chave de operação idempotente vinculada ao SHA-256 do comando canônico. Uma repetição idêntica
retorna o resultado original; conteúdo diferente com a mesma chave é conflito. A máquina de estados
tem versão própria e aceita somente transições explícitas.

Na PoC local, o ator vem de configuração confiável do servidor. Identidade real, autenticação,
papéis e autorização ficam fora desta decisão e são pré-requisitos para qualquer exposição além da
demonstração sintética.

## Alternativas consideradas

- Manter somente colunas de decisão nas sugestões: rejeitado porque perderia histórico e separação
  entre resultado automático e ação humana.
- Permitir edição de eventos: rejeitado porque reduziria a defensabilidade da trilha.
- Aceitar o ator enviado pelo cliente: rejeitado porque permitiria atribuição forjada.
- Usar somente `operation_key`, sem verificar o conteúdo: rejeitado porque comandos diferentes
  poderiam ser confundidos com repetição segura.

## Consequências

- Toda alteração relevante é rastreável e ligada ao sinal original.
- Clientes precisam controlar a versão corrente e gerar chaves de operação únicas.
- O histórico cresce por inserção e exigirá política de retenção antes de dados reais.
- Autenticação e autorização continuam obrigatórias antes de uso multiusuário ou produção.

