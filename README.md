# VBE Hub

Prova de conceito para integrar, correlacionar e apresentar sinais de alerta em saúde pública provenientes de mídia e vigilância comunitária. A solução apoia a triagem humana; não confirma surtos nem toma decisões sanitárias.

Nesta etapa, o projeto usa dados sintéticos em formatos inspirados nas fontes EIOS e Guardiões da Saúde. Conectores reais não fazem parte da validação inicial.

## Objetivo da validação

Até o fim de outubro/início de novembro de 2026, demonstrar que registros heterogêneos podem ser normalizados, correlacionados e consolidados em sinais de alerta revisáveis por um analista.

## Documentação

Comece por [docs/README.md](docs/README.md). As decisões importantes estão em [docs/decisions/README.md](docs/decisions/README.md).

## Estado atual

Fundação, dados sintéticos, funil auditável de correlação, consolidação versionada, prioridade
sugerida explicável e revisão humana auditável estão implementados. O agrupamento automático e o
efeito da revisão foram avaliados sobre 60 eventos e 270 registros sintéticos, com aprovação sob
ressalvas. A capacidade
de correlação da Macroentrega 1 foi aprovada com ressalvas na avaliação exploratória reservada de
30/09/2026; todas as metas previamente definidas foram atendidas. Consulte a [síntese para
profissionais de saúde](docs/health-stakeholder-validation.md), o [protocolo de revisão
humana](docs/human-review-workflow.md) e a [avaliação dos
agrupamentos](docs/grouping-evaluation.md). O painel reutiliza a exportação visual do v0: as rotas
de triagem e ficha técnica consultam os dados sintéticos persistidos pela API canônica, sem usar
mocks como fallback; a ficha também registra revisão humana e atualização de fluxo com confirmação,
versão e trilha de auditoria. A visão em `/kanban` organiza os mesmos sinais canônicos em cinco
estágios, sem permitir mudança por arrastar, e oferece uma tabela acessível equivalente. O panorama
territorial consulta agregados da API, usa geometria local
esquemática e oferece uma lista acessível equivalente, sem expor localização individual nem depender
de tiles externos. O backend também oferece um [resumo de métricas
operacionais](docs/operational-metrics-api.md), reconciliado com a persistência e separado das
evidências de avaliação sintética.
O [experimento integrado](docs/integrated-validation.md) reúne essas evidências de forma
reproduzível e sem novas chamadas ao Gemini. O resultado geral permanece bloqueado porque a linha
de base da extração da ficha técnica ainda não atendeu a todas as metas; isso não altera as
aprovações com ressalvas da correlação e do agrupamento.
Consulte o [contrato de leitura](docs/signal-read-api.md). Autenticação institucional e
integrações reais com EIOS e Guardiões da Saúde permanecem fora desta etapa. A consolidação organiza evidências rastreáveis, mas não confirma
ocorrências nem substitui a triagem de um profissional de saúde.

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

A API estará em `http://localhost:8000` e o painel em `http://localhost:3000`. Triagem e ficha
técnica usam leitura servidor-a-servidor pela rede interna do Compose; o navegador não recebe URL
interna, credenciais ou acesso direto ao banco. Se ainda não houver sinais consolidados, a fila
mostrará o estado vazio canônico. O resumo técnico pode ser consultado sem ferramenta adicional em
`http://localhost:8000/metrics/summary`; ele não confirma eventos de saúde. Verifique:

```bash
docker compose ps
docker compose --profile tools run --rm test
docker compose --profile tools run --rm lint
docker compose --profile tools run --rm frontend-test
docker compose --profile tools run --rm frontend-lint
```

Os checks automatizados também possuem comandos separados para documentação, testes unitários,
integração e smoke test. Consulte o [guia de integração contínua](docs/continuous-integration.md).

### Cenário demonstrativo do painel

Para popular triagem e investigação sem chamar Gemini, carregue o cenário canônico pequeno:

```bash
docker compose --profile tools run --rm demo-load
```

Ele cria três sinais integralmente sintéticos — Dengue em Compensa, Leptospirose em Manaus e
Sarampo ou síndrome compatível — com fontes de mídia e comunidade, fichas, relações, prioridade e
estados diferentes do workflow. Abra `http://localhost:3000/triagem` para a fila ou
`http://localhost:3000/kanban` para o fluxo; o primeiro sinal inicia em `detectado` e permite
exercitar a decisão humana. Repetir o comando não duplica dados nem apaga
ações humanas já registradas.

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

Para repetir a validação integrada sem consumir a cota do Gemini, siga o protocolo e os comandos
em [experimento integrado da PoC](docs/integrated-validation.md#reprodução-sem-consumir-cota-externa).

Consulte o [guia de execução local](docs/development.md) para desenvolvimento com hot reload, portas, volumes, reconstrução sem cache e reset, e o [guia do dataset sintético](docs/synthetic-data-generation.md) para parâmetros, artefatos e reprodutibilidade. O host não precisa de Python, uv, Node.js, PostgreSQL ou Redis.
