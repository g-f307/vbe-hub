---
id: ADR-010
type: adr
status: active
title: "ADR-010: Tratar cada fonte como sinal e formar fichas por decisão humana"
created: 2026-11-08
updated: 2026-11-08
owner: VBE Hub
related_docs:
  - REQ-001
  - DES-001
  - DATA-001
  - API-007
  - API-008
  - ADR-002
  - ADR-006
  - ADR-007
  - ADR-008
---

# ADR-010: Tratar cada fonte como sinal e formar fichas por decisão humana

## Status

Aceita em 2026-11-08 e parcialmente substituída pela ADR-011 quanto à simetria dos membros: toda
ficha agora possui um sinal-cabeça persistente. Persistência, pré-cálculo, API e workflow-v2 foram implementados nas issues
#69 a #72. Interface, demonstração e validação ainda serão migradas nas issues #73 a #77; por
isso, o modelo legado de sinal consolidado permanece disponível temporariamente.

Esta decisão substitui a ADR-006 como modelo operacional futuro de agrupamento. A ADR-007 continua
válida quanto ao uso de regras explicáveis, mas a prioridade passará a referenciar a ficha de
investigação. A ADR-008 permanece válida e será estendida para registrar composição e correção de
fichas.

## Contexto

O modelo inicial transformava automaticamente relações classificadas entre registros em um sinal
consolidado. Embora preservasse vínculos de proveniência, esse desenho fazia o produto chamar de
“sinal” uma unidade derivada e colocava o agrupamento antes da avaliação do analista.

No fluxo operacional desejado, a notícia ou o relato comunitário já é o sinal detectado. A IA deve
ajudar o analista a encontrar outros sinais potencialmente relacionados, sem decidir quais fontes
pertencem à mesma investigação e sem diluir descrições individuais em um resumo consolidado.

A consulta de relacionados também não pode aguardar uma rodada completa do provedor quando a aba é
aberta. A análise precisa ocorrer antecipadamente, com estado e falha observáveis.

## Decisão

### Linguagem de domínio

- **Sinal**: representação individual e auditável de uma fonte coletada. Uma notícia e um relato
  comunitário são dois sinais, ainda que descrevam a mesma situação.
- **Sugestão de relação**: resultado versionado da IA para um par canônico de sinais. É evidência
  de apoio, nunca associação ou decisão sanitária.
- **Ficha de investigação**: agregado criado por comando explícito do analista e composto por um ou
  mais sinais. Organiza a investigação sem copiar, fundir ou sobrescrever os membros.
- **Membro da ficha**: vínculo auditável entre uma ficha e um sinal. O sinal preserva identidade,
  texto, ficha técnica, proveniência e histórico próprios.

Não usar “caso” como sinônimo persistente de sinal ou ficha, pois o termo pode ser confundido com
caso clínico confirmado. Textos de interface podem usar “investigação”, mas os contratos técnicos
usarão nomes explícitos.

### Identidade e invariantes

Cada registro coletado elegível produz no máximo um sinal individual por versão do contrato. A
identidade externa e o hash de conteúdo continuam garantindo idempotência da ingestão.

Uma ficha possui identidade estável e pode conter um único sinal. Um sinal pode pertencer a no
máximo uma ficha ativa; reatribuição exige evento compensatório e controle de concorrência. A
ADR-011 substitui a simetria originalmente definida aqui: o sinal que iniciou a composição é
persistido como cabeça e os demais membros são evidências.

Adicionar ou remover um membro nunca altera o conteúdo do sinal. Correções são novos eventos; não
se atualizam nem apagam decisões anteriores. Uma ficha não pode ficar vazia: remover seu último
membro é inválido, e o encerramento da investigação exige transição explícita com motivo. Um sinal
removido de uma ficha retorna à triagem, não à detecção, porque já houve ação humana. Transferir um
sinal entre fichas ativas deve remover e adicionar no mesmo comando transacional.

### Ciclo operacional

1. A ingestão cria o sinal em `detected`.
2. Extração, indexação, seleção de candidatos e julgamento de relação são executados fora da
   requisição de leitura.
3. O analista inicia a triagem de um sinal por comando explícito; abrir uma tela não muda estado.
4. A aba de relacionados lê sugestões persistidas e informa `pending`, `ready` ou `failed`.
5. O analista seleciona zero ou mais sinais e confirma a criação ou atualização de uma ficha.
6. Uma investigação sem relacionado prossegue em ficha com um único sinal.
7. Sinais associados deixam a fila de detectados, mas permanecem endereçáveis e visíveis como
   membros da ficha.
8. A partir de `verification`, o workflow pertence à ficha de investigação. A tela do sinal mostra
   a ficha ativa e seu estado, sem manter máquinas concorrentes para os membros.

Um sinal pode ser encerrado durante a triagem, com motivo e sem criar ficha. Prosseguir para
verificação sempre exige uma ficha, ainda que com um único membro.

O fluxo permanece `detected → triage → verification → risk_assessment → closed`. Detecção e início
da triagem referem-se ao sinal; verificação, avaliação de risco e encerramento referem-se à ficha.
A transição entre esses limites deve ser atômica, idempotente e auditável.

Na implementação de `workflow-v2`, cada sinal possui uma linha criada junto com sua ingestão e
restrita a `detected`, `triage` ou `closed`. A ficha não recebe uma máquina concorrente durante sua
composição: sua primeira transição explícita cria atomicamente o workflow em `verification` e o
respectivo evento. Depois disso, somente a ficha avança para `risk_assessment` ou `closed`. As
leituras podem projetar o estado da ficha sobre seus membros, mas o histórico próprio do sinal não
é reescrito.

### Relações sugeridas e latência

Busca vetorial e filtros temporal, territorial e clínico reduzem o conjunto de candidatos. O LLM
avalia somente candidatos promissores; não se comparam todos os pares.

As sugestões são calculadas após a preparação da ficha técnica e persistidas com relação,
justificativa, confiança, modelo, versões de prompt/contrato, consumo, latência, erro e validade do
cache. A rota lida pela aba não chama o provedor. Se o processamento ainda não terminou ou falhou,
a interface mostra esse estado e permite investigar o sinal principal normalmente.

### Provedor operacional

OpenAI será o único provedor externo no caminho operacional oficial da PoC para extração,
embeddings e julgamento de relação. As portas `StructuredExtractor`, `EmbeddingProvider` e
`RelationJudge` permanecem neutras para testes e substituição futura. Gemini e Ollama deixam de ser
pré-requisitos de execução; resultados históricos continuam documentados e não serão apagados.

O fallback demonstrativo usa respostas previamente registradas, claramente identificadas. Ele não
é evidência de funcionamento online da IA.

### Prioridade, métricas e visualizações

A prioridade sugerida passa a referenciar a ficha, inclusive quando ela possui um único sinal. Ela
continua explicável, versionada e distinta da avaliação de risco humana.

Métricas devem separar ao menos: sinais coletados, sinais em triagem, sugestões processadas, fichas
ativas e quantidade de membros. Não se pode somar sinais e fichas como se fossem a mesma unidade.
Kanban e mapa devem declarar qual unidade contabilizam.

## Alternativas consideradas

### Manter o sinal consolidado e apenas mudar os rótulos da interface

Rejeitada porque preservaria a decisão automática de agrupamento e continuaria escondendo a unidade
individual atrás de um agregado derivado.

### Criar a ficha automaticamente e pedir confirmação posterior

Rejeitada porque a automação passaria a tomar uma decisão operacional antes do analista e exigiria
desfazer associações possivelmente incorretas.

### Calcular relacionados somente ao abrir a aba

Rejeitada por adicionar latência imprevisível à análise, tornar a interface dependente da quota do
provedor e incentivar repetição de custo.

### Copiar os textos selecionados para um resumo único

Rejeitada porque duplicaria dados, diluiria divergências e enfraqueceria proveniência. Um resumo
derivado poderá existir como visualização, mas nunca substituirá os membros.

### Manter workflow completo independente em cada sinal associado

Rejeitada porque permitiria estados contraditórios para uma mesma investigação e tornaria métricas
e decisões posteriores ambíguas.

## Consequências

- O schema, API, frontend, métricas, demonstração e documentação precisarão de migração coordenada.
- A consolidação automática existente será mantida apenas durante a transição e para evidência
  histórica; não será o modelo canônico futuro.
- O pipeline assíncrono introduz fila, reprocessamento, cache e observabilidade como requisitos.
- A experiência fica mais fiel à atuação humana: a IA encontra candidatos, o analista compõe a
  investigação.
- A quantidade de sinais deixa de equivaler à quantidade de investigações.
- Dados antigos não serão apagados silenciosamente. A migração usará expand/contract e validação
  antes de retirar contratos legados.

## Limites

Esta decisão não define autenticação institucional, integração com fontes reais, política de
retenção de dados reais nem validade clínica ou epidemiológica. Esses itens continuam fora da PoC.
