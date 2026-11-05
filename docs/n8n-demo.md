---
id: DEMO-001
type: guide
status: active
title: Demonstração do fluxo de fontes dispersas com n8n
created: 2026-11-04
updated: 2026-11-05
owner: VBE Hub
related_docs:
  - ADR-004
  - ADR-009
  - API-007
---

# Demonstração do fluxo de fontes dispersas com n8n

Esta demonstração torna visível a problemática central da PoC: uma notícia e um relato comunitário
chegam por caminhos distintos, são processados pelo backend e podem originar um card consolidado
para revisão. Todos os textos são sintéticos. O resultado automático é uma sugestão auditável, não
uma confirmação de evento de saúde.

## O que o fluxo demonstra

O workflow `VBE Hub — lote manual de 10 sinais` contém duas etapas de fonte identificáveis para
cada caso:

- **Fonte 1 — notícia:** simula um registro de mídia;
- **Fonte 2 — relato comunitário:** simula um registro comunitário independente.

O catálogo fechado contém dez pares de fontes com linguagem natural. O texto se parece com o que
poderia chegar de uma notícia local ou canal comunitário, mas os metadados preservam
`synthetic: true` e nenhuma narrativa representa uma ocorrência real.

| Caso | Localização | Conteúdo principal |
| --- | --- | --- |
| `dengue-compensa` | Compensa | Síndrome febril e sinais de alarme. |
| `sarampo-cidade-nova` | Cidade Nova | Febre e exantema em crianças. |
| `leptospirose-jorge-teixeira` | Jorge Teixeira | Sintomas após contato com alagamento. |
| `malaria-taruma` | Tarumã | Febre intermitente e calafrios. |
| `doenca-diarreica-educandos` | Educandos | Diarreia, vômito e dor abdominal. |
| `influenza-parque-dez` | Parque 10 | Síndrome gripal em ambiente escolar. |
| `hepatite-a-colonia-antonio-aleixo` | Colônia Antônio Aleixo | Icterícia e sintomas gastrointestinais. |
| `chikungunya-ponta-negra` | Ponta Negra | Febre e dor articular intensa. |
| `meningite-zumbi` | Zumbi | Síndrome febril com rigidez de nuca. |
| `febre-amarela-reserva-ducke` | Entorno da Reserva Ducke | Síndrome febril após exposição em mata. |

No modo online, cada par é deliberadamente enviado sem uma relação predefinida: a OpenAI estrutura
as fontes e sugere a relação, e o consolidado respeita essa resposta validada. Assim, dez casos de
entrada não garantem dez cards de saída; divergências fazem parte do que deve ser observado.

O n8n apenas apresenta e orquestra a demonstração. Persistência, normalização, ficha técnica,
relação, consolidação e prioridade continuam sob responsabilidade do backend canônico.

## Rodada limpa: estado antes e depois

O reset abaixo remove containers, banco, cache e cadastro local do n8n do projeto `vbe-hub`.
Execute-o somente quando quiser descartar toda a rodada local:

```bash
docker compose -p vbe-hub --profile demo down --volumes
docker compose -p vbe-hub --profile demo up --build --detach --wait
```

Abra o painel em `http://localhost:3000/triagem`. Antes da execução, a fila deve mostrar o estado
vazio. A resposta canônica também pode ser verificada em `http://localhost:8000/signals`.

## Execução manual na interface do n8n

1. Abra `http://localhost:5678`.
2. Se for a primeira execução após o reset, crie a conta proprietária **local** solicitada pelo
   n8n. Não reutilize uma senha institucional.
3. Abra o workflow **VBE Hub — lote manual de 10 sinais**.
4. Abra o nó **Configurar execução manual** e escolha os três campos:

   - `execution_scope`: `single` para um caso ou `batch` para os dez;
   - `case_id`: um identificador da tabela acima; usado somente quando o escopo é `single`;
   - `mode`: `offline` para fixtures gratuitas ou `online` para extração OpenAI.

5. Feche o editor do nó e clique em **Execute workflow**. Esse clique é o único gatilho: não há
   agenda, webhook ou execução automática.
6. Acompanhe **Processar um caso por vez**. Cada item passa por notícia, relato comunitário,
   backend e resultado antes de o próximo começar.
7. Abra ou atualize `http://localhost:3000/triagem`. A quantidade final de cards depende das
   relações sugeridas pela IA: fontes corroborantes podem formar um card; fontes incompatíveis
   permanecem separadas.

Para observar o antes e o depois com mais clareza, comece com `single`, `dengue-compensa` e
`online`. Depois altere para `batch` se o primeiro resultado e o consumo estiverem adequados. Como
a carga é idempotente, o caso inicial não será duplicado.

Para repetir a comparação desde o banco vazio, execute novamente os comandos de reset e subida.

## Modo online opcional

O modo `online` é o padrão da demonstração e chama a OpenAI para duas extrações e uma classificação
de relação por caso. Configure `OPENAI_API_KEY` apenas no `.env` local. Uma rodada completa envolve
até trinta operações lógicas do provedor, sem contar eventuais tentativas automáticas da extração.
O cache persistido evita repetir análises bem-sucedidas para entradas idênticas.

Faça primeiro um caso online e confira o consumo no provedor antes de escolher o lote. No modo
online, a IA estrutura as duas fontes e classifica se são duplicadas, corroborantes, atualizações,
contexto relacionado ou não relacionadas. Essa classificação define se o sistema consolida ou
separa os cards. A rodada continua exploratória e não substitui os protocolos formais de avaliação.

O modo `offline` permanece apenas como contingência. Ele usa fichas e relações congeladas, não
consome API externa e não serve para avaliar o comportamento da IA.

## Segurança e limites

- o workflow não contém chave de API; somente o backend recebe a credencial pelo ambiente;
- escopo, caso e modo são listas fechadas; o lote tem no máximo dez casos;
- a IA não recebe ferramentas e sua saída precisa passar por schema antes da persistência;
- o n8n não recebe acesso ao banco e chama apenas a rota interna da API;
- diagnósticos, catálogo de templates e notificações externas do n8n ficam desativados;
- os dados são sintéticos e não devem ser substituídos por relatos identificáveis;
- a conta local do n8n é apenas para demonstração e não representa autenticação institucional.

Para encerrar sem apagar a evidência local, use:

```bash
docker compose -p vbe-hub --profile demo down
```
