---
id: DEMO-001
type: guide
status: active
title: Demonstração do fluxo de fontes dispersas com n8n
created: 2026-11-04
updated: 2026-11-08
owner: VBE Hub
related_docs:
  - ADR-004
  - ADR-009
  - ADR-010
  - API-007
---

# Demonstração do fluxo de fontes dispersas com n8n

Esta demonstração mostra como uma notícia e um relato comunitário chegam por caminhos distintos,
viram **dois sinais individuais** e recebem uma sugestão de relação. A IA não reúne os sinais e não
cria uma ficha: essa decisão pertence ao analista. Todos os textos são sintéticos, embora tenham
linguagem semelhante à de entradas reais.

## Resultado esperado

O workflow `VBE Hub — lote manual de 20 sinais individuais` percorre dez casos. Cada caso possui:

- uma notícia local, persistida como um sinal;
- um relato comunitário independente, persistido como outro sinal;
- uma análise de compatibilidade disponível na aba **Sinais relacionados**;
- nenhuma ficha de investigação criada automaticamente.

Uma rodada completa termina com **20 sinais em Detectado** e **10 sugestões de relação**. Os mesmos
20 sinais aparecem na fila principal; a sugestão não remove nem oculta o sinal relacionado. Somente
ao abrir um sinal, selecionar a sugestão e confirmar é que o sistema cria uma ficha preservando as
duas descrições originais.

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

O n8n apenas torna o percurso visível e chama a API. Persistência, normalização, extração, relação,
sugestões e composição humana permanecem no backend canônico.

## Preparar uma rodada limpa

O reset abaixo apaga banco, cache e configuração local do n8n do projeto. Use somente quando puder
descartar toda a evidência local:

```bash
docker compose -p vbe-hub --profile demo down --volumes
docker compose -p vbe-hub --profile demo up --build --detach --wait
```

Antes da execução, abra `http://localhost:3000/`: a fila deve estar vazia. A resposta da API pode
ser conferida em `http://localhost:8000/v1/signals`.

## Executar manualmente no n8n

1. Abra `http://localhost:5678`.
2. Na primeira execução após o reset, crie a conta proprietária local solicitada pelo n8n. Não
   reutilize senha institucional.
3. Abra **VBE Hub — lote manual de 20 sinais individuais**.
4. Em **Configurar execução manual**, escolha:

   - `execution_scope`: `single` para um caso ou `batch` para os dez;
   - `case_id`: um identificador da tabela, quando o escopo for `single`;
   - `mode`: `online` para OpenAI ou `offline` para a evidência gravada.

5. Clique em **Execute workflow**. Não há agenda, webhook nem execução automática.
6. Acompanhe **Processar um caso por vez**. Um par termina antes de o próximo começar.
7. Atualize `http://localhost:3000/`. Um caso deve acrescentar dois sinais; o lote, vinte.
8. Abra um sinal, entre em **Sinais relacionados** e examine a justificativa. Os dois cards continuam
   independentes até você selecionar e confirmar a composição.

Repetir o mesmo caso é idempotente: os contadores `created` voltam como zero e nenhum sinal é
duplicado. As sugestões prontas podem ser reapresentadas sem refazer uma chamada já armazenada.

## Modo online e custo controlado

O modo `online` é o percurso que avalia a IA. Configure `OPENAI_API_KEY` somente no `.env` local.
Cada caso pode envolver duas extrações e uma classificação de relação. O lote completo representa
até 30 operações lógicas, sem contar novas tentativas em falhas transitórias.

Comece com `single`, `dengue-compensa` e `online`; confira o resultado e o consumo no provedor antes
de selecionar `batch`. A execução é sequencial e só começa pelo clique do usuário. Resultados
bem-sucedidos são armazenados para evitar custo e demora repetidos.

O modo `offline` usa fichas e relações previamente gravadas (`recorded_fixture`), não chama
provedor externo e serve para ensaiar a apresentação ou operar sem crédito. Ele demonstra o fluxo,
mas **não** constitui uma avaliação da IA.

## Como interpretar a resposta

- `signal_ids`: sempre dois identificadores, um por fonte;
- `association_status: unassociated`: confirma que a API não criou ficha automaticamente;
- `evidence_mode`: `live_openai` ou `recorded_fixture`;
- `created`: informa apenas o que foi criado naquela execução; zero é esperado na repetição;
- `relation` e `relation_explanation`: sugestão auditável, sujeita à revisão humana.

## Segurança e limites

- o workflow não contém chave; somente o backend recebe a credencial pelo ambiente;
- escopo, caso e modo usam listas fechadas e o lote tem no máximo dez pares;
- a IA não recebe ferramentas e sua saída passa por schema antes da persistência;
- o n8n não acessa o banco e chama apenas a rota interna da API;
- diagnósticos, templates e notificações externas do n8n ficam desativados;
- os dados são sintéticos e não devem ser trocados por relatos identificáveis;
- a conta local do n8n não representa autenticação institucional.

Para encerrar preservando os dados:

```bash
docker compose -p vbe-hub --profile demo down
```
