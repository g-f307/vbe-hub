---
id: UI-001
type: design
status: active
title: Fundação do frontend
created: 2026-10-07
updated: 2026-11-08
owner: VBE Hub
related_docs:
  - DES-001
  - OPS-001
  - OPS-002
  - REL-001
---

# Fundação do frontend

> **Fundação atual:** a issue #73 incorporou diretamente o código aprovado do export v0. A #74
> conecta detectados e relacionados ao contrato `/v1`; a #75 acrescenta seleção, confirmação,
> composição e correção humana de fichas. Os adaptadores e as rotas anteriores continuam
> versionados durante a transição.

## Propósito e limite atual

`frontend/` contém o painel versionado do VBE Hub em Next.js/React. O código efetivamente exportado
pelo v0 foi incorporado em `frontend/v0/`; a fila atual preserva sua identidade visual e reutiliza
os componentes compatíveis, sem manter uma segunda aplicação paralela.
Essa separação evita reconstruir o desenho e, ao mesmo tempo, preserva Dockerfile, lockfile, health
check, testes e proxy interno já validados no repositório.

A raiz `/` consulta `GET /v1/signals` no servidor Next. Cada notícia ou relato aparece como card
independente; busca no lote, filtros de estado/fonte e cursor permanecem na URL. Os cards não são
arrastáveis e nenhuma abertura altera workflow. `frontend/v0/lib/mock-data.ts` permanece somente
como artefato transitório de componentes ainda não integrados, nunca como fallback da fila.

As rotas atuais são deliberadamente demonstrativas:

| Rota | Papel na fundação | Estado de dados |
| --- | --- | --- |
| `/` | fila de sinais individuais detectados | consulta `GET /v1/signals`; um card por fonte |
| `/triagem` | fila, filtros, indicadores e paginação | consulta `GET /signals` no servidor Next |
| `/kanban` | quadro complementar dos cinco estágios e tabela acessível | consulta até 100 itens de `GET /signals` com os mesmos filtros; não altera estado |
| `/sinais/[slug]` | página dedicada do sinal, ficha técnica, relacionados, composição humana, proveniência e auditoria | consulta `GET /v1/signals/{id}`, `/related` e `/audit-events`; quando houver ficha ativa, também lê `/v1/investigations/{id}` |
| `/api/investigations/compositions` | BFF da confirmação humana | inicia triagem quando necessário, cria/inclui membros e inicializa a ficha em verificação; aceita somente IDs e chave idempotente |
| `/api/investigations/[fileId]/members/[signalId]/removals` | BFF da correção de vínculo | encaminha somente chave, versão esperada e motivo estruturado |
| `/panorama` | leitura territorial agregada, mapa local e lista acessível | consulta `GET /signals/geographic-summary` no servidor Next |
| `/api/health` | health check do contêiner do painel | retorna somente o estado do serviço |

Os dados de `lib/mock-data.ts` não alimentam detectados, detalhe, triagem, fluxo, investigação nem
panorama. Permanecem apenas como legado do protótipo enquanto outros componentes deixam de depender
deles; não representam situação epidemiológica e não implicam decisão humana.

## Estratégia de migração e rollback

- Fonte local original ignorada: `vbe-hub-frontend/`.
- Código incorporado e versionado: `frontend/v0/`, com imports apenas ajustados ao namespace.
- Infraestrutura preservada: `frontend/Dockerfile`, Compose, health check, proxy, Vitest e ESLint.
- Rotas anteriores preservadas: `/triagem`, `/kanban`, `/sinais/[slug]` e `/panorama`.
- Rollback antes do merge: trocar para `main` ou excluir a branch da issue.
- Rollback depois do merge: reverter o commit/PR da #73; não há migration de banco nem alteração de
  contrato do backend nesta entrega.

A pasta local original não é necessária para build ou execução. Um clone limpo usa somente os
arquivos versionados sob `frontend/`. Os ativos aprovados necessários à aplicação ficam em
`frontend/public/brand/`; o diretório local do brand kit permanece apenas como fonte de trabalho e
continua fora do rastreamento.

## Princípios de apresentação

- A identidade visual usa a assinatura vetorial aprovada da VBE Hub, Geist com fallback Inter,
  azul-petróleo `#155E75`, títulos `#123245`, acento `#0F766E`, fundo `#F6F8FA`, superfícies brancas
  e bordas `#DEE6EA`. Cores de prioridade permanecem reservadas aos respectivos níveis e sempre
  aparecem acompanhadas de texto.
- O painel usa a marcação visível de ambiente de demonstração. Em triagem, fluxo, investigação e panorama,
  sinais, prioridades, decisões e agregados vêm da API e continuam sintéticos.
- A IA continuará sendo apresentada como sugestão auditável. A revisão, justificativa e decisão
  pertencem ao profissional de vigilância.
- A fila e o quadro usam divulgação progressiva: código, estado, condição, local/período e composição de
  fontes ficam no item compacto; evidências, divergências, ficha e auditoria ficam no detalhe.
- A futura visão territorial mostra apenas agregados aprovados por área. Relatos individuais,
  endereço e coordenadas precisas não pertencem ao mapa.

## Fronteira com a API

`lib/individual-signal-read.ts` é a fronteira da fila e do detalhe novos; `lib/signal-read.ts`
permanece como fronteira das rotas legadas. Ambas separam tipos de transporte e apresentação,
valida a resposta mínima, aplica timeout e distingue indisponibilidade, resposta inválida e sinal
inexistente. `VBE_API_INTERNAL_URL` é lida somente no servidor Next e usa `http://api:8000` no
Compose; não há URL interna ou segredo em variável `NEXT_PUBLIC`.

Para escrita, as rotas legadas usam `POST /api/signals/{id}/reviews` e
`POST /api/signals/{id}/workflow/transitions`. A composição nova usa os dois endpoints BFF de
investigação listados acima. As rotas do próprio Next validam UUIDs, mantêm a
URL interna no servidor e encaminham apenas os campos permitidos. Em particular, o navegador não
envia `actor_id`. O backend continua sendo a autoridade para alvo revisável, transição, versão,
idempotência e ator sintético. Erros de validação, indisponibilidade, 404 e conflito de versão são
mostrados no painel; no conflito, a atualização explícita dos dados preserva o formulário local.

Abrir `Sinais relacionados` lê apenas sugestões persistidas. Os estados `pending`, `ready` e
`failed` são exibidos sem iniciar chamada à OpenAI; confiança e justificativa são rotuladas como
sugestão técnica. Marcar candidatos também não escreve: a confirmação mostra o sinal principal,
os candidatos e seus IDs, preserva cada texto separadamente e só então inicia triagem e composição
com chaves idempotentes. Uma ficha ativa exibe membros e eventos; retirar um membro exige motivo,
controle de versão e mantém o evento corretivo. A URL da página e das abas é compartilhável. O parâmetro `returnTo` aceita apenas
destinos internos e preserva filtros, busca e cursor ao voltar para a fila.

O frontend não acessa PostgreSQL, Redis, provedores de IA ou conectores diretamente. A API já
oferece leitura e revisão descritas nos [contratos de leitura](signal-read-api.md) e de [revisão
humana](human-review-workflow.md). Filtros, paginação e modo do quadro são serializados nos parâmetros canônicos da
URL compartilhável. Carregamento, vazio, falha e 404 não usam mocks como fallback. Agregados
territoriais são lidos no servidor Next e o mapa Leaflet é carregado sob demanda, sem tile externo.
A geometria esquemática `demo-areas-v1` fica versionada no frontend; áreas desconhecidas continuam
disponíveis na lista e na fila, marcadas como sem geometria.

O Kanban é uma leitura complementar, não uma segunda máquina de estados. Ele agrupa a mesma
resposta de `GET /signals` em `detectado`, `triagem`, `verificação`, `avaliação de risco` e
`encerrado`. Não há arrastar e soltar: os cartões encaminham para a investigação e para o painel de
decisão auditável. A leitura é limitada explicitamente aos primeiros 100 sinais; quando o total é
maior, a interface orienta reduzir a consulta por filtros ou usar a fila paginada. A alternativa em
tabela, os estados vazios por coluna e a falha com recarga preservam uso por teclado e sem gesto de
arrastar.

## Execução e verificação

Somente Git, Docker e Docker Compose v2 são necessários no host:

```bash
cp .env.example .env
docker compose up --build --detach --wait
```

Abra `http://localhost:3000`. Para verificar isoladamente a fundação no mesmo ambiente que a CI:

```bash
docker compose --profile tools run --rm frontend-lint
docker compose --profile tools run --rm frontend-test
docker compose build frontend
```

O modo de desenvolvimento é opcional e usa recarga automática sem Node.js instalado no host:

```bash
docker compose -f compose.yaml -f compose.dev.yaml up --build
```

Os detalhes de portas, volumes, reconstrução e reset estão em [execução local](development.md).
