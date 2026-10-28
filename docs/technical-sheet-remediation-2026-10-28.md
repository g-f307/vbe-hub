---
id: TEST-006
type: testing
status: active
title: Análise e correção da extração da ficha técnica em 28 de outubro de 2026
created: 2026-10-28
updated: 2026-10-28
owner: VBE Hub
implemented_code:
  - backend/src/vbe_hub/application/ai/technical_sheet.py
  - backend/src/vbe_hub/adapters/ai/gemini.py
  - backend/src/vbe_hub/evaluation/command.py
related_docs:
  - TEST-001
  - TEST-002
  - TEST-005
  - API-004
---

# Análise e correção da extração da ficha técnica em 28 de outubro de 2026

## Motivo da análise

O experimento integrado permaneceu bloqueado porque a linha de base da ficha técnica teve uma
falha em quatro casos e F1 `0,666667` para sintomas. Como o caso que falhou era justamente o relato
comunitário com `febre` e `tosse`, a perda da ficha inteira também apareceu nas métricas como
omissão de sintomas, casos, município, bairro e outros campos.

## Evidência e causa raiz

O relatório histórico identificava a falha como `invalid_response`, mas, por segurança, não
armazenava a resposta bruta nem a mensagem de validação. Portanto, não é possível afirmar qual
trecho exato o modelo devolveu naquele caso.

A investigação do fluxo mostrou uma causa estrutural reproduzível: o Gemini já recebia o JSON
Schema, mas a aplicação aplicava depois uma regra local adicional de grounding literal. Se uma
única evidência não fosse encontrada literalmente na entrada, a ficha completa era rejeitada e o
mesmo pedido era repetido até três vezes. Um teste com uma ficha estruturalmente válida e apenas
uma evidência inválida reproduziu exatamente essa perda integral.

Conclusão defensável: a causa confirmada no código é a granularidade incorreta do tratamento de
grounding. É uma explicação provável para a falha histórica, mas não uma reconstrução comprovada
da resposta original, que não foi retida.

## Correção `extract-v3`

- respostas fora do schema continuam rejeitadas integralmente;
- evidências cujo trecho não existe na origem são removidas;
- somente o campo populado que ficou sem evidência é convertido para `null` ou lista vazia;
- os demais campos válidos e sustentados são preservados;
- campos reparados são contabilizados por registro e por nome no relatório sanitizado;
- a nova versão `extract-v3` invalida o cache da política anterior;
- conteúdo de origem continua delimitado como não confiável, sem ferramentas disponíveis;
- limites de entrada, saída, timeout e tentativas permanecem ativos.

Esse comportamento é conservador: ele nunca cria nem corrige um valor da IA. Apenas elimina o que
não possui sustentação literal, mantendo visível que houve reparo.

## Testes determinísticos

No commit `baf9646`, o teste de regressão falhou antes da correção porque o extrator tentou chamar
o cliente novamente e descartou a ficha. Após a correção:

- o campo sem evidência foi removido;
- sintomas e demais campos sustentados foram preservados;
- uma chamada foi suficiente;
- o relatório registrou o campo reparado sem copiar a narrativa;
- payload fora do schema continuou falhando fechado;
- a suíte final passou com 211 testes unitários e o lint não encontrou violações.

## Tentativa de calibração live

A calibração `e2afc798688862cc` foi iniciada com quatro registros sintéticos, Gemini
`gemini-3.5-flash-lite`, prompt `extract-v3` e schema `technical-sheet-v1`. As quatro requisições
foram recusadas antes da geração, com zero unidades registradas. Uma consulta de metadados
confirmou que a chave possui acesso ao modelo e que ele suporta `generateContent`. Uma chamada
diagnóstica mínima retornou `402 RESOURCE_EXHAUSTED`: os créditos pré-pagos do projeto estão
esgotados.

Essa tentativa é **inválida como avaliação de qualidade**: nenhuma ficha foi produzida. A amostra
reservada não foi executada, evitando chamadas sem possibilidade de sucesso. A linha de base
oficial `3260ec0dc1945093` e o bloqueio do experimento integrado permanecem válidos.

O código passou a distinguir `quota_exhausted` de falha permanente genérica, sem registrar
detalhes da conta. Após recompor a cota, deve-se repetir primeiro a calibração; somente se ela
produzir fichas válidas deve-se executar uma única vez a amostra reservada.

## Interpretação para o cliente

A perda integral causada por um campo sem evidência foi corrigida e protegida por testes. Ainda
não há nova evidência do Gemini para afirmar que a qualidade medida melhorou, porque a conta não
permitiu concluir a calibração. Portanto, a correção está tecnicamente pronta, mas a validação
externa permanece pendente e o resultado global continua bloqueado.

Nada nesta análise demonstra validade clínica ou epidemiológica. Toda ficha continua sendo uma
sugestão auditável e a decisão pertence ao profissional de vigilância.

