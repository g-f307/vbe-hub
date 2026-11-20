---
id: UI-001
type: design
status: active
title: Fundação do frontend
created: 2026-10-07
updated: 2026-11-20
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

A raiz `/` consulta `GET /v1/signals` no servidor Next. Cada notícia ou relato permanece independente
e pode ser visualizado como cards, lista compacta ou Kanban de cinco estados. Busca no lote, filtros,
modo de visualização e cursor permanecem na URL. O Kanban reaproveita a estrutura visual do frontend
exportado, adaptada ao contrato atual; seus cards não são arrastáveis e nenhuma abertura altera workflow.
`frontend/v0/lib/mock-data.ts` permanece somente
como artefato transitório de componentes ainda não integrados, nunca como fallback da fila.

As rotas atuais são deliberadamente demonstrativas:

| Rota | Papel na fundação | Estado de dados |
| --- | --- | --- |
| `/` | fila de sinais individuais em cards, lista ou Kanban | consulta `GET /v1/signals`; um item por fonte |
| `/triagem` | fila, filtros, indicadores e paginação | consulta `GET /signals` no servidor Next |
| `/kanban` | quadro complementar dos cinco estágios e tabela acessível | consulta até 100 itens de `GET /signals` com os mesmos filtros; não altera estado |
| `/sinais/[slug]` | página dedicada do sinal, ficha técnica, relacionados e composição humana | consulta `GET /v1/signals/{id}` e `/related`; quando houver ficha ativa, também lê `/v1/investigations/{id}` |
| `/api/investigations/compositions` | BFF da confirmação humana | inicia triagem quando necessário e cria/inclui membros sem avançar automaticamente para verificação; aceita somente IDs e chave idempotente |
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
  azul principal `#319AD3`, azul de contraste `#076BA4`, coral `#FF624E`, fundo `#F6F8FA`,
  superfícies brancas e bordas `#D2E2EC`. Cores de prioridade permanecem reservadas aos respectivos níveis e sempre
  aparecem acompanhadas de texto.
- O header azul principal usa a assinatura clara aprovada e centraliza a navegação horizontal para
  Detectados, Visão geoespacial e Indicadores. A superfície clara do body sobrepõe sua base com
  cantos superiores arredondados; o azul do header preenche os recortes externos dessa transição. Indicadores
  permanece inativo até que sua rota e seus dados sejam implementados, sem badge auxiliar.
- A hierarquia segue o contrato visual: título de página em 26 px/600, títulos compactos de cards em
  14 px/500, descrições e controles em 13 px e metadados em 12 px. Em triagem, fluxo, investigação e
  panorama, sinais, prioridades, decisões e agregados vêm da API e continuam sintéticos.
- Kanban não prescreve cores universais para estados; ferramentas como Azure Boards permitem regras
  próprias e recomendam consistência. O VBE Hub usa azul para detectado, verde para triagem,
  âmbar para verificação, vermelho para avaliação de risco e cinza para encerrado, em tons mais vivos
  alinhados ao kit 319AD3. Os valores ficam centralizados em `app/globals.css` e os estilos em
  `lib/workflow-visuals.ts`, compartilhados pela fila e pelo modal. Cards, lista e Kanban usam o mesmo mapa; texto
  continua obrigatório, portanto a cor nunca é a única indicação do estágio.
- A IA continuará sendo apresentada como sugestão auditável. A revisão, justificativa e decisão
  pertencem ao profissional de vigilância.
- A fila e o quadro usam divulgação progressiva: código, estado, condição, local/período e composição de
  fontes ficam no item compacto; evidências, divergências, ficha e auditoria ficam no detalhe.
- A visualização em lista organiza cada sinal em Sinal, Fonte, Publicação e Etapa. O tipo de fonte
  aparece diretamente na linha com ícone — grupo de pessoas para relato comunitário e notícia para mídia. Um marcador
  vertical de 4 px, centralizado e recuado das extremidades, repete a cor canônica do estágio no Kanban, sempre acompanhado pelo nome textual;
  em telas estreitas, os mesmos campos são reorganizados verticalmente.
- A visualização em cards mantém três itens por linha em telas amplas, com respiro horizontal moderado
  entre os cartões e aproveitamento maior da largura útil da página.
- Busca, filtros e seletor de visualização da fila usam a borda suave `#D2E2EC`, sem alterar
  o token global dos demais formulários. O anel azul de foco de teclado continua visível.
- Os cards do Kanban usam uma composição compacta e plana, com uma faixa horizontal discreta na cor
  do estágio. Como o nome do estágio já aparece no cabeçalho da coluna, ele não é repetido no card.
- A rota de detalhe funciona como espaço de investigação em largura ampla, não como modal. O cabeçalho
  identifica o registro e a fonte sem expor identificadores
  técnicos; as duas abas **Informações** e **Sinais relacionados** mantêm o estado na URL. Em Informações,
  a ficha técnica ocupa a área principal e a Descrição ocupa o painel lateral responsivo.
  Campos internos de processamento da extração não são apresentados como conteúdo da ficha técnica.
  A ficha apresenta exclusivamente os dez campos operacionais descritos na
  [API individual](individual-signal-api.md#informações-operacionais-da-ficha), com valores ausentes
  como “Não informado”. Os demais atributos da extração permanecem internos.
  A proveniência continua preservada no contrato e no backend, mas não é exposta como aba ao usuário final.
  A composição dispensa a etapa intermediária de revisão: após selecionar sugestões prontas, o analista
  confirma diretamente a inclusão na ficha.
  A composição visual do detalhe usa cabeçalho, faixa de abas e módulos independentes sobre um workspace
  cinza-claro. Ficha técnica, Descrição e evidências ocupam cartões proporcionais, seguindo a nova paleta
  azul 319AD3 e as superfícies neutras do VBE Hub sem introduzir indicadores que não existam no domínio.
  Cabeçalho e abas formam uma única peça encostada ao início do body. O alternador de abas é centralizado
  como uma extensão compacta que começa após o limite inferior do cabeçalho e ocupa somente a largura
  necessária aos seletores, sem criar uma faixa vazia. Em Informações, a ficha técnica projetada ocupa
  a área principal, com o ícone centralizado verticalmente ao lado do conteúdo de cada tópico e a etapa
  atual mantida no workflow, sem tópico adicional na ficha. Quando há composição, a ficha técnica conserva a largura
  original; Descrição e evidências dividem verticalmente a coluna lateral em duas metades, nesta
  ordem, evitando espaço morto ao lado da ficha. Sem evidências incorporadas, o texto original ocupa
  sozinho toda a altura da coluna. Evidências usam uma linha do tempo com o instante da
  incorporação. O mesmo card aparece em grade compacta na aba de gerenciamento, sem repetir o rótulo
  da seção dentro de cada item. Sinais relacionados concentra consulta e remoção dos incorporados e o botão de candidatos; o histórico
  técnico permanece preservado no backend, mas não é exposto nesse espaço operacional.
- O card de evidência incorporada usa faixa violeta `#8054B7`, ícone de vínculo e rótulo
  textual. Essa categoria não representa etapa do Kanban e, por isso, não reutiliza azul, verde, âmbar,
  vermelho ou cinza do workflow; cor nunca é o único indicador do significado.
- A futura visão territorial mostra apenas agregados aprovados por área. Relatos individuais,
  endereço e coordenadas precisas não pertencem ao mapa.

## Aplicação do Brand Kit 319AD3

A fonte local é `vbe-hub-frontend/VBEHub_Brand_Kit_319AD3/`, ignorada pelo Git. O catálogo
`preview/catalogo-visual.png` representa as cores novas; a prancha em `reference/` é histórica.
Somente as duas assinaturas horizontais e o favicon usados foram copiados para `public/brand/`.
O build Docker não depende da pasta original. Não foram alterados desenho, proporções ou
tipografia da logo; os SVGs preservam os pontos coral e não recebem filtros de inversão.

O azul principal é usado no header e na transição do body. `--primary` usa o azul de contraste
para manter legibilidade de links e botões pequenos com texto branco. A navegação do header usa
texto e ícones brancos diretamente sobre o azul principal `#319AD3`, sem faixa de outro azul,
com marcador branco da página atual e realce branco translúcido em hover/seleção. A ação Sair
também mantém o fundo do header. `themeColor` usa `#319AD3`. Essa composição segue a orientação
visual aprovada, mas o contraste branco/azul principal de 3,14:1 fica abaixo da meta de 4,5:1
para texto pequeno; não é apresentada como conformidade integral de contraste da navbar.
Coral é acento da marca, não a semântica de risco/erro.

| Papel | Cor | Texto / superfície de apoio |
| --- | --- | --- |
| Marca / Detectado | `#319AD3` | `#102E40` / `#E7F4FC` |
| Ação primária | `#076BA4` | Branco; hover `#055785` |
| Triagem | `#168653` | Branco / `#E8F7EE` |
| Verificação | `#B77A06` | `#101820` / `#FFF6DC` |
| Avaliação de risco | `#D33449` | Branco / `#FFF0F1` |
| Encerrado | `#626D7C` | Branco / `#F0F3F6` |
| Incorporado | `#8054B7` | Branco / `#F2EAFA` |

As quatro cores de marca são oficiais; workflow, neutros e variantes de interação são tokens
derivados/complementares da interface. Não representam classificação sanitária da IA.
Branco sobre azul principal resulta em aproximadamente 3,14:1; branco sobre azul de contraste,
5,76:1; branco sobre coral, 2,95:1. Por isso os dois primeiros não são intercambiáveis em controles
com texto pequeno. O objetivo é ao menos 4,5:1 em texto normal e 3:1 em texto grande, foco e
componentes funcionais aplicáveis, com rótulos além da cor.

O modal reutiliza `InvestigationComposer` e o Dialog do export v0, com foco contido, Escape,
restauração do foco e rolagem própria em viewport pequena. O contador soma apenas sugestões
prontas, de relação elegível, livres e não incorporadas; a leitura percorre as páginas persistidas
para não ficar limitada aos primeiros 25 itens. Nenhuma abertura dispara extração ou julgamento.
Após confirmação, o estado compartilhado atualiza imediatamente membros, contador e ficha; o
modal fecha e anuncia sucesso. Falhas preservam a seleção e mostram mensagem para nova tentativa.

A consulta de incorporados usa `lib/signal-navigation.ts` para compor o retorno aninhado:
fila → principal → incorporado. A trilha identifica o principal por título e mantém sua aba
(`overview` ou `evidence`) e o endereço completo da fila, incluindo cursor, filtros e visualização.
A leitura direta de um incorporado resolve sua cabeça pela investigação ativa. Destinos externos
ou caminhos ambíguos são rejeitados. A ficha incorporada permanece somente para consulta.
As [evidências da issue #92](evidence/issue-92/README.md) registram testes, percurso e capturas.

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

O botão **Possíveis sinais relacionados**, dentro de Sinais relacionados, abre um modal com sugestões persistidas e ainda inéditas. Os estados `pending`, `ready` e
`failed` são exibidos sem iniciar chamada à OpenAI; uma sugestão pronta é apresentada ao analista apenas
como possível relação, sem transformar confiança técnica em informação operacional. Marcar candidatos também não escreve: a confirmação mostra o sinal principal,
os candidatos por título, preserva cada texto separadamente e só então inicia triagem e composição
com chaves idempotentes. A composição permanece em triagem até uma ação posterior e explícita do
analista. A resposta remove imediatamente os membros incorporados da seleção, sem exigir atualização
manual. O sinal aberto permanece como cabeça; relacionados confirmados deixam a fila, aparecem como
evidências e mantêm uma página própria somente para consulta. `Sinais relacionados` usa a mesma
linguagem visual em uma grade compacta e permite remoção; retirar uma evidência exige motivo,
controle de versão e mantém o evento corretivo. A URL da página e das abas é compartilhável. URLs antigas `tab=related` abrem a aba
Sinais relacionados e seu modal; `tab=evidence` continua abrindo os incorporados. O parâmetro `returnTo` aceita apenas
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
