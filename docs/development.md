---
id: OPS-001
type: operations
status: active
title: Execução e validação local
created: 2026-09-28
updated: 2026-10-07
owner: VBE Hub
related_docs:
  - DES-001
  - ADR-004
---

# Execução e validação local

## Pré-requisitos

- Git;
- Docker Engine ou Docker Desktop;
- Docker Compose v2.

Python, uv, Node.js, PostgreSQL e Redis não precisam ser instalados no host.

## Primeira execução

```bash
cp .env.example .env
docker compose up --build --detach --wait
docker compose ps
```

A API fica disponível em `http://localhost:8000` e o painel em `http://localhost:3000`. As portas
podem ser alteradas por `API_PORT` e `FRONTEND_PORT` no arquivo `.env`. PostgreSQL e Redis
permanecem acessíveis apenas na rede interna da composição. `VBE_API_INTERNAL_URL` é lida apenas
pelo servidor Next e usa `http://api:8000` por padrão; não inclua segredos em variáveis
`NEXT_PUBLIC_`.

As rotas `/triagem` e `/sinais/[slug]` reutilizam o protótipo v0 e leem dados sintéticos
persistidos pela API. O segmento da rota é o UUID canônico. A comunicação ocorre somente no servidor
Next pela rede interna do Compose, sem CORS ou URL interna no navegador. `/panorama` permanece
mockado até sua própria integração.

Para a demonstração do fluxo de revisão, `REVIEW_ACTOR_ID` define o ator sintético registrado na
auditoria e usa `synthetic-analyst` por padrão. Essa configuração não substitui autenticação nem
deve representar uma identidade real. Consulte o [fluxo de revisão](human-review-workflow.md).

Endpoints operacionais:

- `GET /health/live`: confirma que o processo HTTP está ativo;
- `GET /health/ready`: confirma PostgreSQL, extensão pgvector e Redis; retorna HTTP 503 se qualquer dependência estiver indisponível.

Endpoints de leitura usados pelo painel:

- `GET /signals`: fila sintética paginada e filtrável;
- `GET /signals/{signal_id}`: investigação com proveniência, fichas técnicas disponíveis, relações e auditoria.

Consulte o [contrato de leitura canônica](signal-read-api.md). Falha, vazio, carregamento e 404
são exibidos explicitamente e não há fallback silencioso para mocks.

## Verificações oficiais

```bash
docker compose --profile tools run --rm test
docker compose --profile tools run --rm lint
docker compose --profile tools run --rm frontend-test
docker compose --profile tools run --rm frontend-lint
```

Para reproduzir separadamente os checks da CI:

```bash
docker compose --profile tools run --rm docs-check
docker compose --profile tools run --rm --no-deps unit-test
docker compose --profile tools run --rm integration-test
```

O serviço `unit-test` não inicia dependências. O serviço `integration-test` aguarda PostgreSQL com
pgvector, Redis e migrations. Consulte [integração contínua](continuous-integration.md) para a
relação completa entre comandos e checks.

A avaliação determinística dos agrupamentos não usa chave externa nem consome cota:

```bash
EVALUATION_COMMIT=$(git rev-parse --short HEAD) \
  docker compose --profile tools run --build --rm grouping-evaluate
```

Ela gera relatórios sanitizados em `data/reports/`. O protocolo e a rodada oficial estão em
[avaliação de agrupamentos](grouping-evaluation.md).

O gerador, o validador e o importador sintéticos também são ferramentas da composição:

```bash
docker compose --profile tools run --rm synthetic-generate
docker compose --profile tools run --rm synthetic-validate
docker compose --profile tools run --rm synthetic-import
```

Os artefatos massivos ficam em `data/generated/` e o relatório fica em `data/reports/synthetic-validation.json`; ambos são ignorados pelo Git. Consulte [geração e importação de dados sintéticos](synthetic-data-generation.md) para configuração, regras e diagnóstico.

Para reconstruir sem reaproveitar o cache local:

```bash
docker compose build --pull --no-cache
docker compose up --detach --wait
```

O bootstrap cria a extensão `vector` e um usuário não administrador para a aplicação. O schema da aplicação é gerido exclusivamente pelas migrations versionadas.

O serviço `migrate` aplica automaticamente as migrations antes da API. Os comandos abaixo permitem verificar ou operar o histórico sem Alembic instalado no host:

```bash
docker compose run --rm migrate uv run --no-sync alembic current
docker compose run --rm migrate uv run --no-sync alembic upgrade head
docker compose run --rm migrate uv run --no-sync alembic check
```

Downgrade é uma operação de desenvolvimento e pode remover dados. Para testar a reversibilidade da última migration em um banco descartável:

```bash
docker compose run --rm migrate uv run --no-sync alembic downgrade -1
docker compose run --rm migrate uv run --no-sync alembic upgrade head
```

## Smoke test reproduzível

Em uma cópia sem dados locais, o percurso validado pela CI é:

```bash
docker compose build --pull migrate api frontend synthetic-generate synthetic-validate synthetic-import
docker compose up --detach --wait --no-build postgres redis migrate api frontend
docker compose exec -T api python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health/ready', timeout=3)"
docker compose exec -T frontend node -e "fetch('http://localhost:3000/api/health').then((response) => { if (!response.ok) process.exit(1) })"
docker compose run --rm migrate uv run --no-sync alembic check
docker compose --profile tools run --rm synthetic-generate
docker compose --profile tools run --rm synthetic-validate
docker compose --profile tools run --rm synthetic-import
```

A CI também consulta a quantidade persistida e exige os 120 registros da configuração padrão. Use
um nome de projeto Compose exclusivo ou remova intencionalmente os volumes de uma execução anterior
antes de empregar essa contagem como evidência de banco vazio.

## Desenvolvimento com recarga automática

```bash
docker compose -f compose.yaml -f compose.dev.yaml up --build
```

Esse modo monta `backend/src`, `backend/tests` e `frontend/`; o frontend tem recarga automática e
usa volumes nomeados para dependências e artefatos de build. O fluxo de validação e a CI usam as
imagens construídas sem esses volumes. Não execute `npm install` no host: se uma dependência do
frontend precisar mudar, reconstrua a imagem após alterar os arquivos versionados de dependência.

## Persistência e encerramento

`postgres_data` guarda o banco e `redis_data` guarda os snapshots do Redis. O encerramento normal preserva ambos:

```bash
docker compose down
```

O comando abaixo é destrutivo e remove todos os dados locais desses volumes:

```bash
docker compose down --volumes
```

Use o reset apenas quando a perda dos dados locais for intencional. O arquivo `.env` é ignorado pelo Git e não deve conter credenciais reais destinadas ao repositório.

Após um reset, `docker compose up --build --detach --wait` recria o banco, habilita pgvector e reaplica todas as migrations. Backup e restauração não fazem parte desta etapa; os volumes locais não substituem uma política de backup.

## Smoke live opcional do Gemini

Testes e CI não usam chave nem rede externa. Para uma verificação manual, preencha
`GEMINI_API_KEY` somente no `.env` local ignorado pelo Git e execute:

```bash
docker compose --profile live run --rm gemini-live
```

O comando usa exclusivamente a fixture sintética empacotada, não aceita arquivo arbitrário e
imprime apenas ficha, modelo, versões, duração e unidades. Sem chave, termina antes de criar o
cliente de rede. A chave e a narrativa integral não aparecem na saída.

Modelo, timeout, tentativas e limites podem ser ajustados pelas variáveis `GEMINI_MODEL`,
`GEMINI_TIMEOUT_SECONDS`, `GEMINI_MAX_ATTEMPTS`, `GEMINI_MAX_INPUT_CHARS` e
`GEMINI_MAX_OUTPUT_TOKENS`. Para estimar custo sem codificar preços históricos, passe as taxas
observadas no dia da execução:

```bash
docker compose --profile live run --rm \
  -e GEMINI_INPUT_USD_PER_MILLION=VALOR_ATUAL \
  -e GEMINI_OUTPUT_USD_PER_MILLION=VALOR_ATUAL \
  gemini-live
```

Consulte o [contrato da ficha técnica](technical-sheet-contract.md) para schema, segurança,
cache e fontes oficiais de modelo, limites e preços.

## Avaliação live da correlação

Essa avaliação é opcional e não faz parte do início básico. Ela utiliza somente dados sintéticos,
consome cota do provider e exige `GEMINI_API_KEY` no `.env` local. A configuração de avaliação
reservada está congelada no serviço `relation-live-evaluate-v3`.

No Linux, macOS ou Git Bash:

```bash
EVALUATION_COMMIT=$(git rev-parse --short HEAD) docker compose --profile live run --build --rm relation-live-evaluate-v3
```

No PowerShell:

```powershell
$env:EVALUATION_COMMIT = git rev-parse --short HEAD
docker compose --profile live run --build --rm relation-live-evaluate-v3
```

Os relatórios JSON e Markdown e o CSV por caso são gravados em `data/reports/` e ignorados pelo Git por padrão. Somente evidências pequenas e sanitizadas, selecionadas explicitamente, podem ser versionadas.
Consulte a [síntese para profissionais de saúde](health-stakeholder-validation.md) e o [protocolo
técnico da correlação](correlation-evaluation.md). A calibração somente deve ser repetida quando
houver uma nova versão de prompt, política ou dataset; nesse caso, execute primeiro o serviço
`relation-calibrate` e documente a nova identidade experimental.

## Avaliação live da ficha técnica

Com `GEMINI_API_KEY` apenas no `.env`, execute primeiro `EVALUATION_SPLIT=calibration docker compose --profile live run --rm --build technical-sheet-evaluate` e, sem ajustar o prompt pela amostra reservada, repita com `EVALUATION_SPLIT=evaluation`. Os relatórios sanitizados são gravados em `data/reports/`, fora do Git. Consulte o [protocolo de avaliação](technical-sheet-evaluation.md).
