---
id: OPS-002
type: operations
status: active
title: Geração, validação e importação de dados sintéticos
created: 2026-09-28
updated: 2026-09-28
owner: VBE Hub
related_docs:
  - API-001
  - ADR-003
  - ADR-004
---

# Geração, validação e importação de dados sintéticos

## Finalidade e limites

O gerador cria sinais inteiramente sintéticos de mídia e comunidade para exercitar correlação e avaliação. Ele não chama EIOS, Guardiões da Saúde nem modelos de IA, não copia notícias ou relatos reais e não produz identificadores pessoais. Os formatos são inspirados nas necessidades do projeto, sem alegar equivalência a APIs oficiais.

## Geração padrão

Com o arquivo `.env` local configurado conforme o início rápido:

```bash
docker compose --profile tools run --rm synthetic-generate
```

O comando grava `records.jsonl`, `gold.json` e `manifest.json` em `data/generated/`. Executá-lo novamente com a mesma configuração produz arquivos idênticos byte a byte.

## Configuração

Variáveis opcionais podem ser passadas ao Docker Compose:

| Variável | Padrão | Função |
| --- | ---: | --- |
| `SYNTHETIC_SEED` | `307` | Semente explícita da geração. |
| `SYNTHETIC_TOTAL_RECORDS` | `120` | Total de registros. |
| `SYNTHETIC_MEDIA_RATIO` | `0.6` | Fração de registros de mídia. |
| `SYNTHETIC_EVENT_COUNT` | `12` | Quantidade de eventos de referência. |
| `LOCAL_UID` / `LOCAL_GID` | `1000` | Proprietário dos arquivos criados no host. |

Exemplo de lote maior:

```bash
SYNTHETIC_TOTAL_RECORDS=10000 SYNTHETIC_SEED=202610 docker compose --profile tools run --rm synthetic-generate
```

Período, localidades permitidas, idiomas, ruído, campos ausentes, cenários e pesos de relações fazem parte do contrato interno `GeneratorConfig`. Sua exposição futura por arquivo de configuração deve preservar a serialização no manifesto.

## Separação entre entrada e avaliação

`records.jsonl` é a única entrada destinada ao pipeline. `gold.json` é reservado à avaliação e contém `scenario_id`, `gold_event_id` e relações esperadas. Essa separação evita que o motor use a resposta esperada como atributo de entrada.

O manifesto registra semente, versão, configuração efetiva, contagens por fonte/cenário/relação e hashes SHA-256. Para conferir os artefatos:

```bash
sha256sum data/generated/records.jsonl data/generated/gold.json
```

Os valores devem coincidir com `manifest.json`.

## Validação do contrato

Depois da geração, execute:

```bash
docker compose --profile tools run --rm synthetic-validate
```

O comando retorna zero somente para um lote válido. Ele verifica schema, UUIDs, datas com fuso, URLs `.invalid`, unicidade, referências do gold, separação do gabarito, regras determinísticas de privacidade, cenários, proporções, contagens, distribuições, hashes e reprodução integral a partir da configuração do manifesto.

O resumo aparece no terminal. O relatório estruturado é gravado em `data/reports/synthetic-validation.json` e contém:

- estado `valid` ou `invalid`;
- cobertura de registros, cenários e relações;
- total de violações;
- regra, arquivo, mensagem sanitizada e UUID relacionado a cada falha.

O relatório não repete título, narrativa ou payload do registro. Isso evita transformar uma detecção de possível dado pessoal em novo vazamento por log ou artefato.

## Importação idempotente

Com PostgreSQL disponível na composição:

```bash
docker compose --profile tools run --rm synthetic-import
```

O importador persiste registros, proveniência e rótulos de avaliação em estruturas separadas. Uma segunda importação do mesmo lote informa todos os registros como `skipped`, sem duplicá-los.

## Fixture e lotes massivos

`backend/tests/fixtures/synthetic/v1/` contém 12 registros e cobre uma ocorrência de cada cenário obrigatório. O fixture é pequeno e versionado para regressão. `data/generated/` recebe lotes de trabalho e `data/reports/` recebe diagnósticos; ambos permanecem ignorados pelo Git, exceto pelos marcadores dos diretórios.
