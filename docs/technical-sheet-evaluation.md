---
id: TEST-001
type: testing
status: active
title: Avaliação da extração da ficha técnica
created: 2026-09-29
updated: 2026-09-29
owner: VBE Hub
implemented_code:
  - backend/src/vbe_hub/evaluation/
related_docs:
  - API-004
  - ADR-002
  - ADR-003
---

# Avaliação da extração da ficha técnica

Voltar ao [índice da documentação](README.md).

## Protocolo congelado

O experimento `technical-sheet-eval-v1` possui quatro registros de calibração e quatro de
avaliação, com identificadores sem sobreposição. Entradas e gold ficam em arquivos separados;
somente `normalized_data` é entregue ao extrator. A configuração versionada fixa semente,
campos, metas, modelo, normalizador, schema e prompt. Alterar dataset ou qualquer versão muda a
identidade SHA-256 da execução.

As metas são: no máximo 10% de alucinação e 25% de omissão nos campos críticos, F1 mínimo de
0,80 para sintomas e no máximo 5% de falha operacional. Uma taxa operacional acima da meta
impede recomendar qualquer campo para uso direto.

## Reprodução

Com a chave apenas no `.env`, execute primeiro a calibração:

```bash
EVALUATION_SPLIT=calibration docker compose --profile live run --rm --build technical-sheet-evaluate
```

Sem ajustar o prompt a partir da amostra reservada, execute a avaliação:

```bash
EVALUATION_SPLIT=evaluation docker compose --profile live run --rm technical-sheet-evaluate
```

JSON, CSV e Markdown são gravados em `data/reports/`, fora do Git. Eles contêm métricas,
identificadores sintéticos e erros classificados, mas não incluem chave, entrada normalizada,
prompt completo ou resposta bruta do modelo.

## Interpretação

- `direct`: metas do campo e da execução foram atendidas;
- `reduced_weight`: o campo pode auxiliar a busca, mas não deve decidir sozinho;
- `evidence_only`: apresentar ao analista sem usar como chave automática de correlação.

O provider falso valida contratos e determinismo, mas não produz o schema clínico da ficha;
por isso não é comparado como modelo de qualidade. Comparadores perfeitos e casos controlados
são usados como linha de base offline do avaliador.

Esta avaliação mede desempenho técnico em dados sintéticos, não adequação clínica ou
epidemiológica.

