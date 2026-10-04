---
id: API-006
type: api
status: active
title: Prioridade sugerida e explicável
created: 2026-10-03
updated: 2026-10-03
owner: VBE Hub
implemented_code:
  - backend/src/vbe_hub/application/correlation/priority.py
  - backend/src/vbe_hub/adapters/persistence/priority_repository.py
related_docs:
  - API-005
  - DATA-001
  - ADR-007
---

# Prioridade sugerida e explicável

## Finalidade e limite

`priority-v1` sugere uma ordem de triagem para sinais consolidados. O resultado não é avaliação de
risco epidemiológico, confirmação, emergência ou prioridade oficial. Nenhuma notificação ou ação
sanitária é disparada. A decisão continua pertencendo ao profissional de vigilância.

O cálculo é determinístico e não chama LLM. Ele usa exclusivamente dados sintéticos estruturados,
relações já avaliadas e proveniência preservada pelo sinal.

## Contrato do resultado

Cada cálculo contém:

- score inteiro entre 0 e 100 e faixa `routine`, `attention` ou `prompt`;
- confiança entre 0 e 100, separada do score;
- versão e hash da configuração;
- identidade e versão exatas do sinal de entrada;
- componentes com valor, peso, contribuição, explicação, fatos e origens;
- lacunas explícitas e instante de referência do cálculo.

Não existe campo de avaliação humana nesse contrato. A revisão e sua trilha serão outro agregado,
implementado na issue #16.

## Fórmula `priority-v1`

| Componente | Peso | Regra resumida |
| --- | ---: | --- |
| Corroboração | 20% | 0 para uma fonte independente; 0,7 para duas; 1 para três ou mais; atualização acrescenta até 0,1. Registros do mesmo tipo e emissor contam uma vez. |
| Recência | 15% | 1 até 2 dias; 0,75 até 7; 0,5 até 14; 0,25 até 30; 0 após 30, multiplicado pela concentração do período. |
| Geografia | 10% | País 0,25; estado 0,5; município 0,75; bairro/distrito 1. |
| Magnitude | 15% | 0 para zero explicitamente informado; 0,2 para 1–4; 0,5 para 5–19; 0,75 para 20–49; 1 a partir de 50 casos. |
| Gravidade observável | 20% | 1 quando há óbito positivo; 0,6 para sinal grave configurado; 0 apenas quando zero óbitos foi informado; desconhecido quando não há evidência. |
| Completude | 10% | Proporção disponível entre condição, sintomas, tempo, geografia, magnitude e gravidade. |
| Consistência | 10% | Parte de 1 e reduz 0,2 por divergência explícita, até zero. |

Para não transformar desconhecido em ausência de risco, componentes sem informação não entram no
denominador. A fórmula é:

```text
score = arredondar(100 × soma(valor × peso dos componentes conhecidos)
                        ÷ soma(pesos dos componentes conhecidos))
confiança = arredondar(100 × (0,7 × completude + 0,3 × consistência))
```

As faixas são `routine` abaixo de 35, `attention` de 35 a 64 e `prompt` a partir de 65. Elas servem
somente à organização da fila futura.

## Exemplos calculados manualmente

| Cenário sintético | Parcelas conhecidas | Resultado esperado |
| --- | --- | --- |
| Duas fontes independentes, corroboração, 1 dia, município, 10 casos, gravidade desconhecida, completude 5/6 e sem divergência. | `(0,7×0,20 + 1×0,15 + 0,75×0,10 + 0,5×0,15 + 5/6×0,10 + 1×0,10) ÷ 0,80` | Score 78, `prompt`, confiança 88. |
| Uma fonte, mais de 30 dias, país, magnitude e gravidade desconhecidas, completude 4/6 e sem divergência. | `(0×0,20 + 0×0,15 + 0,25×0,10 + 4/6×0,10 + 1×0,10) ÷ 0,65` | Score 29, `routine`, confiança 77. |

Os valores são exemplos técnicos e não representam limiares sanitários validados.

## Idempotência e histórico

A identidade inclui sinal, versão do agrupamento, versão e hash da política de prioridade e instante
de referência. Repetir a mesma entrada é idempotente. Alterar pesos, limites, versão, sinal ou
instante gera outro cálculo, preservando o anterior. A tabela `suggested_priorities` mantém o
resultado e toda a justificativa estruturada.

## Limitações e recalibração

Os pesos e limites são hipóteses de engenharia para validar o fluxo, não recomendações do Africa
CDC nem regras clínicas. A issue #17 deverá avaliar agrupamentos e poderá motivar uma nova versão.
Uma nova configuração nunca deve reinterpretar silenciosamente `priority-v1`.

