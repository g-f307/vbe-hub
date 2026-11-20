---
id: API-009
type: api
status: active
title: API versionada de sinais individuais e fichas
created: 2026-11-08
updated: 2026-11-20
owner: VBE Hub
implemented_code:
  - backend/src/vbe_hub/api/individual_signals.py
related_docs:
  - ADR-010
  - ADR-011
  - API-008
  - DATA-002
  - DES-003
---

# API versionada de sinais individuais e fichas

## Resultado e limite

Os endpoints `/v1` entregam o contrato do novo fluxo sem retirar `/signals`, ainda usado pelo
frontend legado. Um sinal representa exatamente uma notícia ou relato comunitário. A resposta
preserva texto, ficha técnica e proveniência de cada fonte; não cria resumo destrutivo e não expõe
`original_payload`, credenciais ou configurações internas.

Condição, relação e confiança produzidas por IA são sugestões auditáveis. A decisão de colocar
sinais na mesma ficha é sempre um comando explícito do analista. Autenticação institucional está
fora da PoC; `REVIEW_ACTOR_ID` identifica somente o ator demonstrativo registrado no histórico.

## Endpoints

| Método e caminho | Finalidade |
| --- | --- |
| `GET /v1/signals` | Lista sinais livres e sinais-cabeça; evidências ativas não viram cards independentes. |
| `GET /v1/signals/{signal_id}` | Retorna fonte imutável, proveniência e última ficha técnica válida. |
| `GET /v1/signals/{signal_id}/related` | Lê sugestões já calculadas, sem chamar a OpenAI. |
| `POST /v1/investigations` | Cria uma ficha com o primeiro sinal. |
| `GET /v1/investigations/{file_id}` | Retorna cabeça, evidências, projeção técnica, proveniência, conflitos e histórico. |
| `POST /v1/investigations/{file_id}/members/{signal_id}` | Adiciona um sinal por decisão humana. |
| `POST /v1/investigations/{file_id}/members/{signal_id}/removals` | Remove o vínculo por novo evento auditável. |
| `POST /v1/investigations/{file_id}/members/{signal_id}/transfers` | Transfere o sinal atomicamente para outra ficha. |

O OpenAPI navegável permanece em `/docs` e contém os schemas completos.

## Paginação e estados

As coleções usam cursor opaco e ordenação determinística, em vez de `offset`. `limit` aceita de 1
a 100 itens e vale 25 por padrão. Envie `next_cursor` como `cursor` na chamada seguinte. Cursor
inválido retorna `422` com `invalid_cursor`.

`GET /v1/signals` aceita `state` e `source_kind`. A ingestão cria o sinal em `detected`; somente um
comando explícito o move para `triage`. Depois que a ficha inicia `verification`, sua leitura é
projetada sobre os membros para navegação, sem reescrever o workflow próprio dos sinais. Os filtros
aceitam os cinco estados e consultam a unidade proprietária de cada etapa.

`GET /related` aceita `suggestion_status=pending|ready|failed` e devolve apenas candidatos ainda
livres. A cabeça, evidências já vinculadas e membros de outra ficha são excluídos. Cada item informa o estado do
processamento, candidato e data. Em `ready`, pode informar relação, justificativa e confiança; em
`failed`, informa código sanitizado. Abrir a aba nunca chama provedor externo.

## Escritas humanas

Toda escrita exige `operation_key` de 1 a 128 caracteres. Repetir a mesma chave com o mesmo
comando devolve o resultado já registrado, sem duplicar membro ou evento. Reutilizá-la para outro
comando retorna `409 operation_key_conflict`.

Adicionar ou remover membro exige `expected_version`. Versão antiga retorna
`409 investigation_version_conflict` com versões esperada e atual. Um sinal não pode pertencer a
duas fichas ativas; o conflito é `signal_already_assigned`. A última fonte de uma ficha não pode
ser removida, e a cabeça nunca pode ser removida (`investigation_head_cannot_be_removed`). Inclusão, atualização de versão e evento são confirmados ou revertidos juntos na
mesma transação PostgreSQL.

`GET /v1/investigations/{id}` identifica a cabeça em `head_signal_id`. `technical_sheet` é uma
projeção não destrutiva: campos ausentes podem ser preenchidos e listas complementadas pelas
evidências. `technical_sheet_provenance` informa os sinais que sustentam cada caminho de campo;
`technical_sheet_conflicts` preserva alternativas divergentes sem sobrescrever a cabeça.

A transferência recebe as versões esperadas da origem e do destino. A remoção, a inclusão e os
dois eventos são uma única transação: qualquer conflito reverte toda a operação. Repetir a mesma
`operation_key` devolve as duas fichas no estado já registrado, sem duplicar eventos. Origem e
destino iguais retornam `409 investigation_transfer_same_file`.

Criar ficha ou adicionar membro exige que o sinal esteja em `triage`; caso contrário, a API retorna
`409 signal_not_in_triage`. A composição não inicia verificação automaticamente: o sinal-cabeça permanece
visível em triagem e prosseguir usa um comando explícito no workflow da ficha documentado em
[revisão humana e auditoria](human-review-workflow.md).

Exemplo sanitizado de criação:

```json
{
  "signal_id": "018f6d5d-9c44-7b10-8000-000000000001",
  "operation_key": "triage-session-001"
}
```

## Compatibilidade

### Informações operacionais da ficha

O detalhe individual e a investigação retornam também `information`. A ficha exibida usa somente
Descrição (`source.body`), Confidencialidade, Tipo de sinal, Etiologia, Perigo geral, Perigo
específico, Etiquetas, Data do sinal, Data de detecção e Data de notificação. Os atributos antigos
de `technical_sheet` continuam disponíveis para correlação, auditoria e consumidores existentes,
mas não são apresentados como campos adicionais na ficha.

| Campo de `information` | Origem e comportamento |
| --- | --- |
| `confidentiality` | `original_payload.signal_information.confidentiality`, texto operacional explícito ou `null`. Não representa confiança da IA nem implementa controle de acesso institucional. |
| `signal_type` | `original_payload.signal_information.signal_type`, texto explícito ou `null`. Não é tipo de fonte nem etapa do fluxo; nenhum enum é inventado a partir do exemplo “Abertura”. |
| `etiology` | Metadado explícito `etiology`; na ausência, `technical_sheet.disease_or_condition`, preservando suspeita e qualificadores. |
| `hazard_general` / `hazard_specific` | Categorias explícitas de `signal_information`; sem dado, `null`. Não são deduzidas da síndrome nem atribuídas por confiança de extração. |
| `tags` | Lista explícita `signal_information.tags`, normalizada por espaços/casefold e sem duplicatas. Não copia sintomas automaticamente nem traduz termos sem vocabulário aprovado. |
| `signal_date` | Data ISO ou timestamp com fuso informado na origem; na ausência, início válido de `technical_sheet.temporal`. Não usa publicação como fallback nem inventa hora. |
| `detected_at` | Coleta da origem em `provenance.collected_at`. Para cargas `demo-scenario` / `vbe-hub-demo`, cujo timestamp é simulado e retroativo, retorna `null` em vez de apresentá-lo como detecção real. O timestamp original continua na proveniência. Não reutiliza publicação ou incorporação como detecção. |
| `notified_at` | Timestamp explícito com fuso em `signal_information.notified_at` ou `null`; nenhuma notificação é presumida. |
| `origins` | Mapa campo → caminho de origem (`source:…`, `extraction:…` ou `provenance:…`). |

`signal_information` é um envelope opcional do payload de origem já persistido em JSONB. Não há
migration, atualização destrutiva ou reextração obrigatória. Textos aceitam até 200 caracteres,
etiquetas até 50 itens de 80 caracteres; valores inválidos são ignorados campo a campo, mantendo a
fonte original consultável. Nenhum atributo novo gera inferência ou chamada ao provedor durante a
consulta. Ausência vira “Não informado” na interface.

Exemplo parcial de **metadados declarados por uma fonte sintética**, antes da importação:

```json
{
  "signal_information": {
    "confidentiality": "Nível 1",
    "signal_type": "Abertura",
    "etiology": "Dengue (suspeita)",
    "hazard_general": "Arbovirose",
    "hazard_specific": "Dengue",
    "tags": ["dengue", "febre", "arbovirose"],
    "signal_date": "2026-11-14",
    "notified_at": "2026-11-20T08:00:00-04:00"
  }
}
```

Esses valores são exemplares, não defaults da aplicação. O importador preserva os metadados junto
ao payload; esta entrega não adiciona edição manual nem integração externa de notificação.

Na investigação, `information_provenance` e `information_conflicts` acompanham a projeção.
Etiologia, perigos, etiquetas e data do sinal podem ser complementados pelos membros; divergências
escalares preservam a cabeça e registram alternativa/origem. Confidencialidade, tipo de sinal,
detecção e notificação pertencem à cabeça e não são herdados de evidências. Remover um membro
recalcula essa leitura sem modificar as fontes ou as extrações originais.

`/signals`, seu detalhe, workflow e métricas consolidadas permanecem disponíveis durante a
estratégia expand/contract. Novos consumidores devem usar `/v1`. A retirada do contrato legado
exigirá uma decisão posterior, atualização do frontend e evidência de que nenhum consumidor ainda
depende dele.

## Validação

Os testes cobrem coleção limitada, OpenAPI, detalhe e proveniência, sugestões pendentes e falhas,
criação, repetição, conflito de idempotência, concorrência otimista, remoção por evento e
preservação dos textos individuais:

```bash
docker compose --profile tools run --build --rm integration-test \
  uv run --no-sync pytest tests/integration/api/test_individual_signal_api.py
```

Os dados da PoC são sintéticos e a API não representa validação clínica ou epidemiológica.
