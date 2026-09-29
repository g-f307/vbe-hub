---
id: API-001
type: api
status: active
title: Contrato de dados sintéticos
created: 2026-09-28
updated: 2026-09-28
owner: VBE Hub
planned_code:
  - backend/
related_docs:
  - REQ-001
  - DES-001
  - ADR-003
---

# Contrato de dados sintéticos

## Propósito

Os dados sintéticos devem permitir repetir experimentos e medir corretamente a correlação. Cada registro mantém um `scenario_id` e um `gold_event_id`, invisíveis ao motor em produção, mas disponíveis à avaliação.

## Envelope comum

| Campo | Tipo | Descrição |
| --- | --- | --- |
| `id` | UUID | Identificador do registro. |
| `source_kind` | enum | `media` ou `community`. |
| `source_name` | texto | Veículo, canal ou aplicativo sintético. |
| `published_at` | data/hora | Momento em que a informação foi publicada/reportada. |
| `title` | texto opcional | Título, usual para mídia. |
| `body` | texto | Narrativa original sintética. |
| `source_url` | URL sintética opcional | Referência de origem; não deve apontar a pessoa real. |
| `provenance` | objeto | Gerador, versão e semente usados. |

## Entrada inspirada em mídia/EIOS

Além do envelope: idioma, veículo, URL, data de publicação, título, resumo/narrativa e possível localidade ou tópico. O gerador deve produzir republicações, textos em português e outros idiomas, detalhes conflitantes e notícias preventivas para testar falsos agrupamentos.

## Entrada inspirada em comunidade/GdS

Além do envelope: município/bairro, janela temporal, sintomas relatados, contagem agregada, grupo/ambiente afetado e precisão geográfica. Não gerar nem aceitar identificadores pessoais, telefone, endereço residencial, idade exata ou localização individual.

## Ficha técnica extraída

O modelo deve retornar JSON validado com: `natureza_do_registro`, `doenca_ou_agravo`, `patogeno`, `sindrome`, `sintomas`, `casos_estimados`, `obitos_estimados`, `grupo_afetado`, `inicio_evento`, `fim_evento`, `precisao_temporal`, `pais`, `estado`, `municipio`, `bairro_distrito`, `local_especifico`, `precisao_localizacao`, `ambiente`, `acao_em_andamento`, `e_sinal_relevante`, `confianca_extracao` e evidências textuais por campo.

Valores desconhecidos permanecem nulos; o modelo não pode inventar doença, data, lugar ou número de casos.

## Relações de referência

Cada par candidato pode ser rotulado como:

- `duplicate`: mesma informação republicada ou copiada.
- `corroboration`: fontes independentes descrevem o mesmo evento.
- `update`: acrescenta informação sobre evento existente.
- `related_context`: ação preventiva, campanha ou contexto associado, mas não evidência do evento.
- `unrelated`: não representa o mesmo evento.

## Cenários mínimos

- Surto local confirmado por notícia e relatos agregados compatíveis.
- Sintomas semelhantes em bairros ou datas incompatíveis.
- Republicações da mesma matéria.
- Campanha de vacinação relacionada a uma doença, mas sem evidência de casos.
- Doença desconhecida com sintomas compartilhados e informação incompleta.
