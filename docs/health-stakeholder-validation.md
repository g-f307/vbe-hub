---
id: REPORT-001
type: report
status: active
title: Validação da correlação para profissionais de saúde
created: 2026-09-30
updated: 2026-09-30
owner: VBE Hub
related_docs:
  - REQ-001
  - API-007
  - TEST-003
---

# Validação da correlação para profissionais de saúde

## Resumo executivo

O VBE Hub foi testado para responder a uma pergunta prática: **o sistema consegue reconhecer
quando sinais provenientes de fontes diferentes podem estar falando sobre a mesma situação de
saúde pública?**

Foram criadas situações sintéticas semelhantes às que a aplicação deverá receber, como uma
notícia sobre casos de sarampo em um município e relatos comunitários de pessoas com febre e
manchas vermelhas no mesmo lugar e período. O sistema comparou esses sinais, sugeriu o tipo de
relação e apresentou uma justificativa rastreável.

Na avaliação reservada, todos os cenários receberam o tratamento esperado e não houve falha de
comunicação com o serviço de IA. O resultado sustenta a **viabilidade técnica inicial da função de
correlação**, com ressalvas: foram usados dados sintéticos, uma amostra exploratória e uma única
execução. O teste não confirma surtos, não mede validade clínica ou epidemiológica e não substitui
a análise do profissional de vigilância.

## O que foi construído

A capacidade avaliada recebe fichas técnicas com problema de saúde ou síndrome, sintomas, local,
período, quantidade mencionada e resumo da fonte. A partir delas, o sistema:

1. descarta comparações claramente incompatíveis, por exemplo, por distância temporal ou
   geográfica;
2. encaminha pares plausíveis para regras seguras ou para o modelo de IA;
3. sugere a relação entre os sinais;
4. registra fontes de origem, justificativa, confiança e versão do método;
5. mantém o resultado como sugestão para revisão humana.

Essa função apoia detecção e pré-triagem na Vigilância Baseada em Eventos. Verificação, avaliação
de risco, confirmação de evento e decisão de resposta permanecem sob responsabilidade da
vigilância em saúde.

## Relações traduzidas para situações de vigilância

| Relação | Significado para a vigilância | Exemplo sintético |
| --- | --- | --- |
| Mesmo conteúdo | Duas fontes parecem republicar ou parafrasear a mesma informação. | Duas notícias mencionam a mesma doença, município, data e quantidade. |
| Corroboração | Uma fonte independente acrescenta evidência compatível sobre a ocorrência. | Notícia sobre sarampo e relato comunitário de febre e manchas vermelhas no mesmo local e período. |
| Atualização | Um registro posterior modifica ou amplia informação sobre o mesmo evento. | Informe posterior eleva a quantidade de casos anteriormente mencionada. |
| Contexto relacionado | O conteúdo trata do mesmo tema, mas não apresenta nova evidência de ocorrência. | Campanha de vacinação ou orientação preventiva relacionada à doença noticiada. |
| Sem relação | Os sinais não devem ser consolidados como parte do mesmo evento. | Doenças, locais ou períodos incompatíveis, ou conteúdo sem contexto verificável. |

## Método de validação

### Casos com resposta conhecida

Foram preparados 50 casos de referência, distribuídos igualmente entre os cinco tipos de relação.
Para cada caso, a resposta esperada foi definida antes da avaliação. Também foram incluídas 200
comparações distratoras para verificar se o sistema evitava aproximar registros que não deveriam
ser consolidados.

Os dados foram inteiramente sintéticos. Eles não contêm dados pessoais, prontuários, relatos
identificáveis ou informações reais sobre surtos.

### Separação entre preparação e prova

Os exemplos usados para ajustar o método foram separados dos exemplos usados na avaliação final.
As partes possuem identificadores, períodos e redações diferentes. A resposta esperada da
avaliação ficou fora da entrada do modelo e só foi consultada depois que as sugestões foram
produzidas.

Essa separação reduz o risco de apresentar como validação aquilo que o sistema já havia visto
durante os ajustes.

### Casos fáceis e casos ambíguos

A avaliação não se limitou a cópias idênticas. Incluiu diferenças de quantidade, relatos sem o
nome explícito da doença, atualizações posteriores, conteúdo preventivo, campos ausentes,
incompatibilidade geográfica e instruções maliciosas inseridas no texto. Isso testa fronteiras
relevantes e a capacidade de tratar o conteúdo recebido como dado não confiável.

### Execução reprodutível e auditável

A execução ocorreu no ambiente Docker versionado. Foram identificados a amostra, a semente, o
modelo, a orientação dada à IA, as regras e o código avaliado. A ordem dos casos foi embaralhada
de maneira reprodutível para evitar que uma interrupção externa atingisse sempre o mesmo tipo de
situação.

Cada sugestão pode ser ligada às duas fichas de origem e à justificativa produzida. O profissional
pode entender por que os sinais foram aproximados, em vez de receber apenas uma decisão opaca.

## O que aconteceu na avaliação

A avaliação descrita neste documento corresponde à execução reservada `ce77f037927356db`,
realizada em 30/09/2026 sobre o commit `f5a57cb`, com o modelo
`gemini-3.5-flash-lite`. Esses identificadores permitem conferir a evidência técnica sem expor
credenciais ou dados reais.

O sistema examinou 250 comparações. A maior parte foi descartada na pré-triagem, evitando enviar
comparações evidentemente irrelevantes para a IA. Quarenta e quatro comparações foram analisadas
pelo Gemini e cinco foram resolvidas por regra determinística de conteúdo equivalente.

Todos os casos de referência e distratores receberam o tratamento esperado. O sistema:

- reconheceu os dez cenários de corroboração por fontes independentes;
- diferenciou corroboração de conteúdo apenas preventivo ou contextual;
- reconheceu as dez atualizações de eventos;
- identificou conteúdos equivalentes sem depender sempre da IA;
- manteve separados os sinais sem relação;
- concluiu as 44 consultas à IA sem falhas operacionais.

O caso central da proposta — relacionar uma notícia sobre sarampo com relatos comunitários de
febre e manchas vermelhas no mesmo município e período — foi reconhecido como corroboração, com
justificativa baseada na compatibilidade de local, tempo e sintomas.

## Por que o resultado é defensável

O resultado não depende de uma demonstração escolhida manualmente. Ele foi obtido por procedimento
previamente definido, com respostas conhecidas, conjunto reservado, cenários negativos, registro
da configuração e preservação das tentativas anteriores que falharam. Uma rodada anterior,
afetada pela indisponibilidade da API, permaneceu registrada como bloqueada; ela não foi apagada
nem reinterpretada como sucesso.

Também existe separação de responsabilidades: a IA propõe relações e explica sua sugestão,
enquanto o profissional verifica as fontes, corrige ou rejeita o agrupamento e decide sobre
investigação ou resposta.

## O que este resultado permite afirmar

> Em um conjunto controlado de sinais sintéticos, o VBE Hub demonstrou capacidade inicial de
> reduzir comparações irrelevantes e sugerir corretamente relações entre notícias e relatos
> comunitários, mantendo justificativa e vínculo com as fontes para revisão humana.

## O que ainda não pode ser afirmado

- que o sistema confirma doença, surto ou emergência de saúde pública;
- que o desempenho será o mesmo com dados reais e linguagem não controlada;
- que a amostra representa toda a diversidade epidemiológica, cultural e linguística de Manaus;
- que as futuras integrações reais com EIOS e Guardiões da Saúde já foram validadas;
- que uma única execução pequena demonstra estabilidade estatística;
- que o agrupamento sugerido dispensa verificação e avaliação de risco profissional.

## Próximas validações recomendadas

1. submeter exemplos e justificativas a profissionais da vigilância para avaliar utilidade,
   clareza e riscos de interpretação;
2. permitir que esses profissionais aceitem, corrijam ou rejeitem sugestões na interface;
3. ampliar gradualmente diversidade e quantidade de casos, preservando um conjunto reservado;
4. testar dados anonimizados ou controlados mais próximos da operação real, mediante autorização
   e governança adequadas;
5. avaliar separadamente extração das fichas, correlação, formação do sinal consolidado e fluxo de
   decisão humana.

## Roteiro curto para apresentação ao cliente

1. **Problema:** sinais relacionados chegam por fontes e linguagens diferentes e podem passar
   despercebidos quando analisados isoladamente.
2. **Proposta:** o VBE Hub organiza os sinais e sugere quais podem representar o mesmo evento.
3. **Demonstração:** mostrar notícia sobre sarampo e relato de sintomas compatíveis, com as fichas,
   a sugestão e a justificativa.
4. **Prova controlada:** explicar os 50 casos conhecidos e 200 distratores, separados dos exemplos
   de ajuste.
5. **Resultado:** todos os cenários receberam o tratamento esperado nesta avaliação exploratória.
6. **Governança:** reforçar que a sugestão é auditável e a decisão sanitária continua humana.

[Consultar o protocolo técnico](correlation-evaluation.md) · [Voltar ao índice](README.md)
