# VBE Hub

Prova de conceito para integrar, correlacionar e apresentar sinais de alerta em saúde pública provenientes de mídia e vigilância comunitária. A solução apoia a triagem humana; não confirma surtos nem toma decisões sanitárias.

Nesta etapa, o projeto usa dados sintéticos em formatos inspirados nas fontes EIOS e Guardiões da Saúde. Conectores reais não fazem parte da validação inicial.

## Objetivo da validação

Até o fim de outubro/início de novembro de 2026, demonstrar que registros heterogêneos podem ser normalizados, correlacionados e consolidados em sinais de alerta revisáveis por um analista.

## Documentação

Comece por [docs/README.md](docs/README.md). As decisões importantes estão em [docs/decisions/README.md](docs/decisions/README.md).

## Estado atual

Fundação, dados sintéticos, funil auditável de correlação e consolidação versionada de sinais estão implementados. A capacidade
de correlação da Macroentrega 1 foi aprovada com ressalvas na avaliação exploratória reservada de
30/09/2026; todas as metas previamente definidas foram atendidas. Consulte a [síntese para
profissionais de saúde](docs/health-stakeholder-validation.md) e o [protocolo
técnico](docs/correlation-evaluation.md). Interface web e integrações reais com EIOS e Guardiões
da Saúde ainda não foram implementadas. A consolidação organiza evidências rastreáveis, mas não
confirma ocorrências nem substitui a triagem de um profissional de saúde.

## Início rápido

### Execução básica sem Gemini

Com Git, Docker e Docker Compose v2:

```bash
git clone https://github.com/g-f307/vbe-hub.git
cd vbe-hub
cp .env.example .env
docker compose up --build --detach --wait
```

No PowerShell, substitua a cópia do arquivo por:

```powershell
Copy-Item .env.example .env
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

### Avaliação opcional com Gemini

A execução básica, os testes e os dados sintéticos não exigem chave externa. Para repetir a
avaliação de correlação com o Gemini, configure `GEMINI_API_KEY` somente no `.env` local e siga o
[guia de execução local](docs/development.md#avaliação-live-da-correlação). Essa etapa consome
cota do provider e não é necessária para iniciar a aplicação.

Consulte o [guia de execução local](docs/development.md) para desenvolvimento com hot reload, portas, volumes, reconstrução sem cache e reset, e o [guia do dataset sintético](docs/synthetic-data-generation.md) para parâmetros, artefatos e reprodutibilidade. O host não precisa de Python, uv, PostgreSQL ou Redis.
