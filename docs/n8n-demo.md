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

Cada par é classificado como corroborante para formar exatamente um card. Essa relação é uma
fixture demonstrativa, não uma conclusão produzida ou validada pela IA.

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
7. Abra ou atualize `http://localhost:3000/triagem`. No escopo `batch`, a rodada concluída deve
   apresentar dez cards; cada card conserva duas origens.

Para observar o antes e o depois com mais clareza, comece com `single`, `dengue-compensa` e
`offline`. Depois altere para `batch` e execute os nove casos ainda ausentes. Como a carga é
idempotente, o caso inicial não será duplicado.

Para repetir a comparação desde o banco vazio, execute novamente os comandos de reset e subida.

## Modo online opcional

O modo `offline` usa fichas sintéticas congeladas e não consome API externa. Para demonstrar a
extração com OpenAI, configure `OPENAI_API_KEY` apenas no `.env` local e troque `mode` para
`online`. Um caso faz no máximo duas extrações; o lote completo faz no máximo vinte. O cache
persistido evita nova cobrança para entradas idênticas.

Faça primeiro um caso online e confira o consumo no provedor antes de escolher o lote. No modo
online, a IA estrutura as fontes, mas a relação dos dez casos continua predefinida para que a
apresentação seja repetível. Esta demonstração não mede acurácia e não substitui os protocolos de
avaliação do projeto.

## Segurança e limites

- o workflow não contém chave de API; somente o backend recebe a credencial pelo ambiente;
- escopo, caso e modo são listas fechadas; o lote tem no máximo dez casos;
- o n8n não recebe acesso ao banco e chama apenas a rota interna da API;
- diagnósticos, catálogo de templates e notificações externas do n8n ficam desativados;
- os dados são sintéticos e não devem ser substituídos por relatos identificáveis;
- a conta local do n8n é apenas para demonstração e não representa autenticação institucional.

Para encerrar sem apagar a evidência local, use:

```bash
docker compose -p vbe-hub --profile demo down
```
