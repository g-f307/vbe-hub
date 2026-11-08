# VBE Hub

Prova de conceito para integrar, correlacionar e apresentar sinais de alerta em saúde pública provenientes de mídia e vigilância comunitária. A solução apoia a triagem humana; não confirma surtos nem toma decisões sanitárias.

Nesta etapa, o projeto usa dados sintéticos em formatos inspirados nas fontes EIOS e Guardiões da Saúde. Conectores reais não fazem parte da validação inicial.

## Objetivo da validação

Demonstrar que fontes heterogêneas podem ser normalizadas como sinais individuais, relacionadas por
IA e organizadas pelo analista em fichas de investigação auditáveis, sem apagar ou fundir as
descrições de origem.

## Documentação

Comece por [docs/README.md](docs/README.md). As decisões importantes estão em [docs/decisions/README.md](docs/decisions/README.md).

## Estado atual

> **Transição em andamento em 08/11/2026:** a fundação visual nova já executa na rota `/`, mas
> ainda usa a carga local explicitamente marcada como demonstração. As rotas legadas continuam
> disponíveis como referência de integração até a migração funcional das issues #74 e #75. A
> [ADR-010](docs/decisions/ADR-010-individual-signals-human-investigation.md) redefine cada fonte
> como sinal individual. As tabelas, o worker assíncrono, a [API `/v1`](docs/individual-signal-api.md)
> e o workflow-v2 já existem. Nenhuma sugestão da
> IA associa fontes automaticamente.

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
Uma [análise posterior](docs/technical-sheet-remediation-2026-10-28.md) corrigiu a perda integral
de fichas causada por grounding de um único campo. A reavaliação continua pendente porque a
calibração foi recusada por créditos esgotados antes de gerar respostas; portanto, a linha de base
não foi substituída.
Em 04/11/2026, uma [avaliação alternativa com OpenAI](docs/openai-technical-sheet-evaluation-2026-11-04.md)
gerou oito fichas sintéticas sem falhas e atendeu às metas dos campos centrais da correlação. A
evidência é exploratória, baseada em amostra pequena, e não substitui validação clínica ou
epidemiológica.
Consulte os contratos de leitura [legado](docs/signal-read-api.md) e de [sinais
individuais](docs/individual-signal-api.md). Autenticação institucional e
integrações reais com EIOS e Guardiões da Saúde permanecem fora desta etapa. A consolidação atual
organiza evidências rastreáveis, mas não confirma ocorrências nem substitui a triagem de um
profissional de saúde. Ela será preservada como evidência histórica enquanto o novo modelo é
implementado.

## Início rápido

### Execução básica sem provedor externo

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

A API estará em `http://localhost:8000` e o painel em `http://localhost:3000`. Sem
`OPENAI_API_KEY`, o worker permanece ocioso e a aplicação continua disponível para dados
pré-carregados. Triagem e ficha
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

Para uma apresentação visual do percurso notícia + relato comunitário, com comparação verificável
entre fila vazia e até dez cards consolidados, use o profile n8n descrito no [guia da demonstração
de fontes dispersas](docs/n8n-demo.md). A execução é manual e sequencial; o modo online avalia
extração e relação com OpenAI, enquanto o modo offline existe somente como contingência.

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

### Processamento opcional com OpenAI

Para preparar novas sugestões de relacionados, configure `OPENAI_API_KEY` somente no `.env` local
e reinicie `relation-worker`. O worker executa extração, embedding, pré-seleção limitada e
julgamento de relação fora da requisição da interface. A fila aceita no máximo 1.000 sinais por
padrão, consulta 20 vizinhos e envia no máximo três candidatos por sinal ao modelo; todos os
limites são configuráveis pelas variáveis `RELATED_*`. Abrir a futura aba de relacionados apenas
lerá os estados persistidos `pending`, `ready` ou `failed`.

### Avaliações históricas opcionais

A execução básica, os testes e os dados sintéticos não exigem chave externa. Gemini não participa
do fluxo operacional. Para repetir a avaliação histórica de correlação, configure
`GEMINI_API_KEY` somente no `.env` local e siga o
[guia de execução local](docs/development.md#avaliação-live-da-correlação). Essa etapa consome
cota do provider e não é necessária para iniciar a aplicação.

A extração da ficha técnica também pode ser avaliada com OpenAI, sem mudar embeddings ou
correlação. Configure `OPENAI_API_KEY` somente no `.env` local e siga o
[protocolo da ficha](docs/technical-sheet-evaluation.md). Execute primeiro os quatro casos de
calibração e só use os quatro casos reservados se a calibração for operacionalmente válida.

Para repetir a validação integrada sem consumir a cota do Gemini, siga o protocolo e os comandos
em [experimento integrado da PoC](docs/integrated-validation.md#reprodução-sem-consumir-cota-externa).

Consulte o [guia de execução local](docs/development.md) para desenvolvimento com hot reload, portas, volumes, reconstrução sem cache e reset, e o [guia do dataset sintético](docs/synthetic-data-generation.md) para parâmetros, artefatos e reprodutibilidade. O host não precisa de Python, uv, Node.js, PostgreSQL ou Redis.
