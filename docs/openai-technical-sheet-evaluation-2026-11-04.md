---
id: EVID-009
type: evidence
status: active
title: Avaliação exploratória da ficha técnica com OpenAI em 04/11/2026
created: 2026-11-04
updated: 2026-11-04
owner: VBE Hub
related_docs:
  - TEST-001
  - API-004
  - ADR-002
---

# Avaliação exploratória da ficha técnica com OpenAI em 04/11/2026

Voltar ao [índice da documentação](README.md).

## Pergunta avaliada

O experimento verificou se um segundo provedor consegue transformar relatos sintéticos de mídia e
comunidade na ficha técnica `technical-sheet-v1`, preservando evidências literais e os campos que
ajudam a encontrar sinais sobre o mesmo evento. Ele não avaliou diagnóstico, confirmação de surto,
risco epidemiológico ou decisão sanitária.

## Método

- provedor/modelo: OpenAI / `gpt-6-luna`;
- prompt/schema/normalizador: `extract-v3` / `technical-sheet-v1` / `1.0.0`;
- quatro casos de calibração e quatro casos reservados, sem sobreposição;
- somente o registro normalizado foi enviado ao modelo;
- saída estruturada estrita, sem ferramentas e sem armazenamento pelo provedor;
- validação local de schema, limites e correspondência literal das evidências;
- calibração executada antes da amostra reservada, sem ajuste intermediário do prompt.

As entradas e os gabaritos são sintéticos e versionados. Os relatórios completos da execução ficam
em `data/reports/`, fora do Git, para não transformar artefatos de execução em dependência do
repositório.

## Resultados

| Rodada | Identidade | Fichas válidas | Falhas | Sintomas | Campos centrais | Custo estimado |
| --- | --- | ---: | ---: | --- | --- | ---: |
| Calibração | `65652b2c5d447f58` | 4/4 | 0 | F1 1,00 | condição, casos e localização sem omissão/alucinação | US$ 0,0009058 |
| Reservada | `3a4037d5ad668836` | 4/4 | 0 | F1 1,00 | condição, casos, município, bairro e início com 100% de acerto | US$ 0,0008926 |

Na calibração, um valor de confiança sem evidência literal foi removido pelo mecanismo local de
grounding; a ficha foi preservada e o reparo ficou registrado. Na amostra reservada não houve
reparo. As duas rodadas somaram 8.019 unidades de entrada, 1.993 de saída e custo estimado de
US$ 0,0017984 com os preços configurados no dia da execução.

O campo `suggested_relevance` apresentou normalização divergente e omissões. Ele foi corretamente
classificado como `evidence_only`: pode ser mostrado ao analista, mas não deve definir prioridade
nem correlação automaticamente. Os campos centrais aprovados continuam sendo sugestões
auditáveis, sempre vinculadas aos registros de origem.

## Leitura para profissionais de saúde

Nos oito exemplos, o sistema conseguiu organizar corretamente as informações mais úteis para
aproximar relatos: qual condição foi mencionada, quais sintomas apareceram, quantas pessoas foram
citadas, onde e quando ocorreu. Ele também evitou criar esses dados quando não estavam no texto.
Isso sustenta o uso da ficha como apoio à triagem e à busca de relatos relacionados; não sustenta
que a condição mencionada exista de fato ou que represente um surto.

## Limitações

- oito casos são uma amostra pequena, sintética e exploratória;
- os exemplos não representam toda a linguagem, geografia ou diversidade epidemiológica real;
- o resultado não compara significância estatística entre OpenAI e Gemini;
- preço, modelo e comportamento do serviço externo podem mudar;
- validação com profissionais e dados reais anonimizados permanece necessária antes de qualquer
  uso operacional.

Portanto, a evidência aprova tecnicamente o adapter e o protocolo para a PoC, com ressalvas de
generalização. Ela não constitui validação clínica ou epidemiológica.
