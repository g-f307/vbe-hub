# VBE Hub

Prova de conceito para integrar, correlacionar e apresentar sinais de alerta em saúde pública provenientes de mídia e vigilância comunitária. A solução apoia a triagem humana; não confirma surtos nem toma decisões sanitárias.

Nesta etapa, o projeto usa dados sintéticos em formatos inspirados nas fontes EIOS e Guardiões da Saúde. Conectores reais não fazem parte da validação inicial.

## Objetivo da validação

Até o fim de outubro/início de novembro de 2026, demonstrar que registros heterogêneos podem ser normalizados, correlacionados e consolidados em sinais de alerta revisáveis por um analista.

## Documentação

Comece por [docs/README.md](docs/README.md). As decisões importantes estão em [docs/decisions/README.md](docs/decisions/README.md).

## Estado atual

Fundação executável da API: FastAPI, PostgreSQL com pgvector, persistência auditável e Redis são reproduzíveis por Docker Compose. Ainda não há pipeline analítico, interface web ou integração com APIs reais.

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

Consulte o [guia de execução local](docs/development.md) para desenvolvimento com hot reload, portas, volumes, reconstrução sem cache e reset. O host não precisa de Python, uv, PostgreSQL ou Redis.
