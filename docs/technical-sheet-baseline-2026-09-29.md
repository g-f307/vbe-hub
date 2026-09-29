---
id: TEST-002
type: testing
status: active
title: Linha de base da ficha técnica em 29 de setembro de 2026
created: 2026-09-29
updated: 2026-09-29
owner: VBE Hub
related_docs:
  - TEST-001
  - API-004
---

# Linha de base da ficha técnica em 29 de setembro de 2026

Voltar ao [índice da documentação](README.md).

## Configuração

- execução reservada: `3260ec0dc1945093`;
- dataset: `technical-sheet-eval-v1`, SHA-256
  `d09e4bcc02df42e6dc3659caf63d9656b72617362d9b655aaf63d582dc1ccf7a`;
- provider/modelo: Gemini / `gemini-3.5-flash-lite`;
- prompt/schema/normalizador: `extract-v2` / `technical-sheet-v1` / `1.0.0`;
- amostra: quatro registros sintéticos reservados.

O `extract-v2` foi criado após a calibração mostrar omissão de evidência para campos derivados.
Nenhum ajuste foi realizado depois de observar a rodada reservada.

## Resultado

Três fichas foram válidas e uma permaneceu inválida após as tentativas permitidas: taxa de falha
operacional de 25%, acima da meta de 5%. A latência foi 13.824 ms no p50 e 17.203 ms no p95.
A execução bem-sucedida registrou pelo menos 1.090 tokens de entrada e 1.686 de saída; a versão
seguinte do executor passou a somar também o consumo de tentativas rejeitadas. Portanto, esses
números são um limite inferior e não devem ser apresentados como custo total exato.

Pela tabela paga vigente na data da execução (US$ 0,30 por milhão de tokens de entrada e
US$ 2,50 por milhão de tokens de saída), o limite inferior seria US$ 0,004542. Na camada gratuita,
o custo faturado pode ser zero. Preços devem ser reconfirmados antes de cada experimento na
[tabela oficial do Gemini](https://ai.google.dev/gemini-api/docs/pricing).

| Campo crítico | Resultado principal | Decisão |
| --- | --- | --- |
| doença/agravo | acurácia 1,00; sem alucinação ou omissão | peso reduzido pelo gate operacional |
| sintomas | F1 0,667; omissão 0,50 | peso reduzido |
| casos estimados | MAE 0 nos pares; omissão 0,333 | peso reduzido |
| óbitos estimados | acurácia 1,00 | peso reduzido pelo gate operacional |
| início temporal | acurácia 1,00 | peso reduzido pelo gate operacional |
| município | omissão 0,333; sem alucinação | peso reduzido |
| bairro/distrito | omissão 0,50; sem alucinação | peso reduzido |

Campos não críticos permanecem apenas como evidência exibida. Nenhum campo está liberado para
uso direto nesta linha de base. O tamanho reduzido da amostra torna os resultados exploratórios;
uma rodada maior e pré-registrada será necessária antes da validação final do TCC.
