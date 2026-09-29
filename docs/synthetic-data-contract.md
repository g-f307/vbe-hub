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

Os dados sintéticos devem permitir repetir experimentos e medir corretamente a correlação. `scenario_id`, `gold_event_id` e relações esperadas ficam exclusivamente no artefato gold, separado dos registros entregues ao pipeline.

## Envelope comum

| Campo | Tipo | Descrição |
| --- | --- | --- |
| `id` | UUID | Identificador do registro. |
| `source_kind` | enum | `media` ou `community`. |
| `source_name` | texto | Veículo, canal ou aplicativo sintético. |
| `external_id` | texto | Identificador estável na fonte sintética. |
| `published_at` | data/hora | Momento em que a informação foi publicada/reportada. |
| `title` | texto opcional | Título, usual para mídia. |
| `body` | texto | Narrativa original sintética. |
| `source_url` | URL sintética opcional | Referência de origem; não deve apontar a pessoa real. |
| `provenance` | objeto | Gerador, versão e semente usados. |

O envelope do pipeline não contém rótulos de avaliação. O importador pode associar `scenario_id` à proveniência persistida e `gold_event_id` à tabela de avaliação, sem acrescentá-los ao registro bruto.

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

## Artefatos canônicos

- `records.jsonl`: um envelope de entrada por linha, sem rótulos gold;
- `gold.json`: rótulos por registro e relações esperadas entre pares;
- `manifest.json`: configuração, contagens, versão e hashes SHA-256 dos outros dois arquivos.

O fixture pequeno versionado está em `backend/tests/fixtures/synthetic/v1/`. Lotes de escala ficam em `data/generated/` e são ignorados pelo Git.
