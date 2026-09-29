---
id: API-006
type: api
status: active
title: Seleção de pares candidatos
created: 2026-09-30
updated: 2026-09-30
owner: VBE Hub
implemented_code:
  - backend/src/vbe_hub/application/correlation/candidates.py
related_docs:
  - API-004
  - API-005
  - REQ-001
---

# Seleção de pares candidatos

A seleção reduz os vizinhos semânticos aos pares plausíveis que poderão seguir para julgamento de
relação. Ela é determinística, explicável e não confirma que dois registros representam o mesmo
evento.

## Política inicial

Os parâmetros `max_temporal_gap_days`, `geographic_level`, `minimum_semantic_score` e
`minimum_total_score` são fornecidos pela composição da aplicação. A configuração inicial dos
testes usa janela de 14 dias, compatibilidade até município e mínimos de 0,70 para similaridade
semântica e 0,65 para o score total.

O score combina componentes entre zero e um:

| Componente | Peso | Cálculo |
| --- | ---: | --- |
| semântico | 0,50 | similaridade de cosseno recebida da busca vetorial |
| clínico | 0,25 | média das concordâncias disponíveis de doença, patógeno, síndrome e sintomas |
| temporal | 0,125 | decai linearmente até o limite da janela |
| geográfico | 0,125 | aumenta conforme os níveis conhecidos e compatíveis |

Conflito em qualquer nível geográfico conhecido até o nível configurado ou distância temporal
acima da janela causa exclusão, independentemente do score. Informação temporal ou geográfica
ausente recebe valor neutro 0,5, em vez de exclusão automática. Isso permite manter um registro
incompleto quando os componentes clínico e semântico fornecem evidência suficiente.

Datas podem chegar como objetos ou strings ISO. Comparações textuais removem espaços excedentes e
ignoram maiúsculas/minúsculas. Empates são ordenados pelo identificador estável, garantindo o mesmo
resultado para as mesmas entradas e parâmetros.

## Casos de referência

| Caso | Semântico | Clínico | Temporal | Geográfico | Total | Resultado/motivo |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| mesmo quadro, data e município | 0,90 | 1,00 | 1,00 | 1,00 | 0,950 | inclui |
| diferença exatamente de 14 dias | 0,90 | 1,00 | 0,00 | 1,00 | 0,825 | inclui na borda |
| diferença de 15 dias | 0,90 | 1,00 | 0,00 | 1,00 | 0,825 | exclui: janela excedida |
| sem data/local, clínica compatível | 0,92 | 1,00 | 0,50 | 0,50 | 0,835 | inclui com lacunas registradas |
| município conflitante | 0,95 | 1,00 | 1,00 | 0,00 | 0,850 | exclui: conflito geográfico |
| baixa evidência clínica e semântica | 0,30 | 0,00 | 1,00 | 1,00 | 0,400 | exclui: mínimos não atingidos |

Cada decisão conserva os quatro componentes, o score final e razões estáveis, incluindo lacunas,
conflitos, mínimos não atingidos ou `candidate_selected`. A próxima etapa pode auditar esses dados,
mas não deve tratar a seleção como classificação definitiva.

## Segurança e limites

Os filtros operam somente sobre fichas já validadas e identificadores de registros de origem. Não
há execução de conteúdo textual, SQL dinâmico ou chamada a modelo nesta etapa. Nesta PoC só entram
dados sintéticos. Antes de dados multi-organização, o isolamento de acesso deverá ocorrer também
na busca vetorial; filtrar posteriormente na aplicação não é isolamento suficiente.

## Validação reproduzível

```bash
docker compose run --rm unit-test
```

Os testes cobrem as fronteiras de 14/15 dias, nível geográfico configurável, lacunas, baixa
evidência, razões, componentes e ordenação determinística.

[Voltar ao índice da documentação](README.md)
