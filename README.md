# VBE Hub

Prova de conceito para integrar, correlacionar e apresentar sinais de alerta em saúde pública provenientes de mídia e vigilância comunitária. A solução apoia a triagem humana; não confirma surtos nem toma decisões sanitárias.

Nesta etapa, o projeto usa dados sintéticos em formatos inspirados nas fontes EIOS e Guardiões da Saúde. Conectores reais não fazem parte da validação inicial.

## Objetivo da validação

Até o fim de outubro/início de novembro de 2026, demonstrar que registros heterogêneos podem ser normalizados, correlacionados e consolidados em sinais de alerta revisáveis por um analista.

## Documentação

Comece por [docs/README.md](docs/README.md). As decisões importantes estão em [docs/decisions/README.md](docs/decisions/README.md).

## Estado atual

Fundação, dados sintéticos, normalização, extração auditável da ficha técnica e indexação semântica versionada estão implementados. A seleção determinística de pares candidatos está em implementação. A linha de base reservada do Gemini foi executada e recomenda peso reduzido ou somente evidência; julgamento das relações, interface web e integrações EIOS/GdS ainda não foram implementados.

## Início rápido

Com Git, Docker e Docker Compose:

```bash
git clone https://github.com/g-f307/vbe-hub.git
cd vbe-hub
cp .env.example .env
docker compose up --build --detach --wait
```

A API estará em `http://localhost:8000`. Verifique:

```bash
docker compose ps
docker compose --profile tools run --rm test
docker compose --profile tools run --rm lint
```

Os checks automatizados também possuem comandos separados para documentação, testes unitários,
integração e smoke test. Consulte o [guia de integração contínua](docs/continuous-integration.md).

Gere, valide e importe o dataset sintético padrão:

```bash
docker compose --profile tools run --rm synthetic-generate
docker compose --profile tools run --rm synthetic-validate
docker compose --profile tools run --rm synthetic-import
```

Consulte o [guia de execução local](docs/development.md) para desenvolvimento com hot reload, portas, volumes, reconstrução sem cache e reset, e o [guia do dataset sintético](docs/synthetic-data-generation.md) para parâmetros, artefatos e reprodutibilidade. O host não precisa de Python, uv, PostgreSQL ou Redis.
