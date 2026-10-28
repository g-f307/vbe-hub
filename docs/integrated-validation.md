---
id: TEST-005
type: testing
status: active
title: Experimento integrado da prova de conceito
created: 2026-10-27
updated: 2026-10-27
owner: VBE Hub
implemented_code:
  - backend/src/vbe_hub/evaluation/integrated_experiment.py
  - compose.yaml
related_docs:
  - TEST-002
  - TEST-003
  - TEST-004
  - API-009
---

# Experimento integrado da prova de conceito

## Pergunta respondida

O experimento reúne as evidências necessárias para responder se a prova de conceito sintética é
reproduzível e se cada parte crítica atingiu as metas técnicas definidas antes das avaliações. Ele
não confirma surtos, não mede utilidade epidemiológica e não transfere a decisão sanitária para a
IA.

Em linguagem operacional: verificamos se outra pessoa consegue gerar os dados, conferir sua
integridade, iniciar a aplicação, observar sinais com registros de origem, repetir o agrupamento e
consultar as avaliações congeladas de extração e correlação. A aprovação geral somente ocorre
quando todas as etapas críticas atendem às suas metas.

## Desenho da validação

A evidência é composta por camadas identificadas, porque repetir todas as chamadas ao Gemini a
cada alteração consumiria a cota gratuita sem acrescentar uma nova amostra independente:

1. **Reprodução atual dos dados:** geração determinística de 120 registros com semente `307`,
   validação de contrato e verificação dos hashes dos arquivos de registros e referência.
2. **Reprodução operacional atual:** carga idempotente do cenário demonstrativo pelo mesmo
   repositório de persistência da aplicação, resultando em 6 registros de origem, 6 registros
   normalizados, 6 fichas, 3 relações, 3 sinais e 3 prioridades, sem lacunas de reconciliação.
3. **Extração e correlação congeladas:** reutilização das rodadas oficiais com Gemini, mantendo
   identidade, data, versão do dataset, resultados e limitações. Nenhuma chamada ao provedor é
   feita pelo experimento integrado.
4. **Agrupamento atual:** repetição determinística com 60 eventos e 270 registros, seguida pela
   simulação de uma decisão humana auditável sobre uma relação incorreta.

Essas camadas não são apresentadas como se os 120 registros tivessem percorrido, em uma única
rodada ao vivo, todas as etapas. O importador em massa persiste registros e referências, mas não
aciona sozinho todo o processamento de IA; o cenário demonstrativo materializa o percurso
operacional de forma determinística. Essa separação evita uma conclusão mais ampla do que a
evidência permite.

## Resultado oficial de 27/10/2026

- implementação avaliada: commit `23c7cc6`;
- identidade integrada: `c3bf8f07bb729c8a`;
- dados gerados: 120 registros, 12 eventos de referência e 60 relações, sem erros de contrato;
- agrupamento: F1 par a par `0,983607` antes e `1,000000` depois da revisão;
- chamadas ao Gemini nesta repetição: zero;
- resultado geral: **bloqueado**.

| Etapa | Resultado | Explicação para validação do cliente |
| --- | --- | --- |
| Integridade dos dados | Atendeu | Os mesmos parâmetros produzem arquivos identificáveis por hash e nenhum erro de contrato foi encontrado. |
| Operação da aplicação | Atendeu | O banco reconciliou todas as etapas do cenário demonstrativo e preservou o vínculo com as fontes sintéticas. |
| Extração da ficha | Não atendeu | Na rodada oficial, uma de quatro extrações falhou e a identificação de sintomas ficou abaixo do nível esperado. |
| Correlação | Atendeu com ressalvas | A amostra reservada pequena atingiu as metas técnicas, mas não demonstra generalização para fontes reais. |
| Agrupamento e revisão | Atendeu com ressalvas | Houve uma união incorreta controlada; a decisão humana registrada separou os eventos sem apagar o histórico. |

O bloqueio não significa que toda a PoC falhou. Significa que ela é reproduzível e que correlação,
agrupamento e revisão apresentaram o comportamento esperado na amostra sintética, mas a extração
da ficha técnica ainda não sustenta a aprovação do conjunto. A falha permanece visível em vez de
ser diluída pelas etapas aprovadas.

## Limitações e uso correto

- a extração e a correlação usam amostras exploratórias pequenas e sintéticas;
- a reprodução integrada reutiliza resultados congelados do Gemini e não é uma nova repetição do
  provedor;
- o cenário operacional contém seis registros e serve para verificar integração e
  rastreabilidade, não desempenho em grande escala;
- as relações do ensaio de agrupamento são sintéticas e congeladas;
- não houve fontes reais do EIOS ou Guardiões da Saúde;
- os resultados não demonstram validade clínica ou epidemiológica.

A ficha, a relação, o agrupamento e a prioridade produzidos pela IA continuam sendo sugestões
auditáveis. A decisão final pertence ao profissional de vigilância.

## Reprodução sem consumir cota externa

Em um clone com `.env` configurado, use um projeto Compose isolado. As portas alternativas evitam
conflito com uma aplicação já iniciada:

```bash
API_PORT=18022 FRONTEND_PORT=13022 docker compose -p vbe-hub-validation up --build --detach --wait postgres redis migrate api
docker compose -p vbe-hub-validation --profile tools run --build --rm synthetic-generate
docker compose -p vbe-hub-validation --profile tools run --build --rm synthetic-validate
docker compose -p vbe-hub-validation --profile tools run --build --rm demo-load
API_PORT=18022 FRONTEND_PORT=13022 EVALUATION_COMMIT=$(git rev-parse --short HEAD) docker compose -p vbe-hub-validation --profile tools run --build --rm integrated-evaluate
```

O último comando grava um JSON auditável e um resumo em linguagem direta em `data/reports/`, que é
ignorado pelo Git. O JSON distingue `current_reproduction` de `frozen_official_run`, registra
versões, sementes, hashes, commit e identidades, e não copia credenciais nem relatos brutos.

Para encerrar preservando os volumes isolados:

```bash
API_PORT=18022 FRONTEND_PORT=13022 docker compose -p vbe-hub-validation down
```

Excluir os volumes é opcional e destrutivo; não é necessário para consultar os artefatos gerados.

