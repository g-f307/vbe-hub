---
id: API-007
type: api
status: active
title: Revisão humana e trilha de auditoria
created: 2026-10-06
updated: 2026-11-08
owner: VBE Hub
implemented_code:
  - backend/src/vbe_hub/application/workflow.py
  - backend/src/vbe_hub/adapters/persistence/workflow_repository.py
  - backend/src/vbe_hub/api/workflow.py
related_docs:
  - API-005
  - API-006
  - DATA-001
  - ADR-008
---

# Revisão humana e trilha de auditoria

> **Compatibilidade:** `workflow-v1` continua disponível para sinais consolidados históricos. O
> contrato canônico novo é `workflow-v2`, descrito abaixo, com uma fonte por sinal e workflow da
> ficha a partir da verificação.

## Workflow-v2 implementado

- o sinal individual nasce em `detected` e entra em `triage` somente por comando explícito;
- abrir detalhe ou aba não muda estado;
- a seleção humana cria uma ficha com um ou mais sinais e mantém o conjunto em `triage`;
- iniciar `verification` exige uma ação posterior e explícita do analista;
- a partir de `verification`, a ficha possui o workflow compartilhado;
- sinais membros preservam histórico, URL e conteúdo, mas não mantêm máquinas posteriores
  concorrentes;
- inclusão e remoção são eventos append-only, idempotentes e sujeitos a versão;
- transferência entre fichas é atômica, idempotente e verifica as duas versões;
- um sinal não pode pertencer a duas fichas ativas.

Um sinal é associado somente depois de `detected → triage`. Sua remoção de uma ficha mantém o
workflow próprio em `triage`; o estado posterior da ficha nunca é copiado sobre esse histórico.
A primeira transição da ficha é `triage → verification`, versão `0 → 1`, registrada somente quando
o analista aciona o avanço; ela não faz parte da composição. Depois, a ficha aceita `verification → risk_assessment`, retorno para `verification` e
encerramento explícito com motivo.

| Método e caminho | Finalidade |
| --- | --- |
| `GET /v1/signals/{id}/workflow` | Estado próprio do sinal. |
| `POST /v1/signals/{id}/workflow/transitions` | Iniciar triagem ou encerrar durante a triagem. |
| `GET /v1/signals/{id}/audit-events` | Histórico próprio do sinal. |
| `GET /v1/investigations/{id}/workflow` | Estado da ficha após iniciar verificação. |
| `POST /v1/investigations/{id}/workflow/transitions` | Iniciar/avançar/encerrar investigação. |
| `GET /v1/investigations/{id}/audit-events` | Histórico do workflow compartilhado. |
| `GET /v1/metrics/summary` | Contagens separadas de sinais, sugestões e fichas. |

Toda escrita recebe `operation_key`, `expected_version`, ator do servidor, motivo quando necessário
e comentário opcional. Repetição idêntica devolve o evento original; versão concorrente retorna
`409 workflow_version_conflict`. A IA não possui rota nem permissão para alterar estados.

## Finalidade e limite

O fluxo permite que um analista aceite, corrija ou rejeite sugestões de relação, pertencimento,
agrupamento e prioridade. A ação humana fica separada do resultado automático e não confirma um
evento de saúde pública. Nesta PoC, o ator é uma identidade sintética configurada no servidor; não
há autenticação, autorização ou integração com diretório institucional.

## Estados e transições

A máquina `workflow-v1` usa os valores abaixo. Somente as setas declaradas são aceitas.

```mermaid
flowchart LR
  D[detected] --> T[triage]
  T --> V[verification]
  V --> T
  V --> R[risk_assessment]
  R --> V
  T --> C[closed]
  V --> C
  R --> C
```

O encerramento exige um motivo estruturado: `duplicate`, `insufficient_evidence`,
`not_public_health_event`, `resolved` ou `other`. Um sinal encerrado não pode ser reaberto em
`workflow-v1`; uma política futura deverá receber outra versão.

## Revisões

Cada revisão aponta para o identificador do objeto e para a identidade imutável da sugestão. O
servidor confirma que o alvo pertence ao sinal antes de registrar a decisão.

| Campo | Valores ou regra |
| --- | --- |
| `target_type` | `relation`, `membership`, `grouping` ou `priority` |
| `action` | `accept`, `correct` ou `reject` |
| `corrected_value` | Obrigatório em `correct`; até 20 campos escalares limitados |
| `reason_code` | Obrigatório em `correct` e `reject` |
| `comment` | Contexto opcional de até 500 caracteres |

Uma nova sugestão, com outra identidade, não apaga a decisão anterior. Uma correção também não
altera eventos já gravados: ela cria um novo evento compensatório cujo `previous_value` referencia
a decisão vigente e cujo `new_value` registra o novo entendimento.

## Concorrência, repetição e auditoria

O cliente envia `expected_version`. Se outro analista já alterou o fluxo, a API responde `409` com
`workflow_version_conflict`, evitando sobrescrita silenciosa. Cada escrita também exige uma
`operation_key`:

- repetir a mesma chave com conteúdo idêntico retorna o evento já criado;
- reutilizar a chave com conteúdo diferente retorna `operation_key_conflict`;
- uma impressão SHA-256 do conteúdo canônico comprova a equivalência da repetição.

Os eventos preservam ator, instante, versão, ação, alvo, valor anterior, valor novo, motivo e
comentário. A tabela `review_events` aceita somente inserções; um gatilho do PostgreSQL rejeita
alterações e exclusões. O vínculo com o sinal e suas evidências de origem permanece intacto.

## API

| Método e caminho | Finalidade |
| --- | --- |
| `GET /signals/{signal_id}/workflow` | Consultar estado e versão correntes. |
| `POST /signals/{signal_id}/workflow/transitions` | Avançar, retornar ou encerrar conforme a máquina. |
| `POST /signals/{signal_id}/reviews` | Registrar decisão sobre uma sugestão. |
| `GET /signals/{signal_id}/audit-events` | Consultar o histórico em ordem. |

Exemplo de transição para triagem:

```json
{
  "operation_key": "triage-0001",
  "expected_version": 0,
  "target_state": "triage",
  "comment": "Sinal sintético encaminhado para análise."
}
```

Exemplo de aceitação de agrupamento, usando a `identity_key` retornada pelo sinal:

```json
{
  "operation_key": "review-grouping-0001",
  "expected_version": 1,
  "target_type": "grouping",
  "target_id": "00000000-0000-0000-0000-000000000001",
  "suggestion_identity_key": "HASH_SHA256_DA_SUGESTAO",
  "action": "accept",
  "comment": "As evidências sintéticas tratam do mesmo evento provável."
}
```

O ator não é aceito no corpo da requisição. Configure `REVIEW_ACTOR_ID` no `.env`; o valor padrão
é `synthetic-analyst`. Isso facilita a demonstração reproduzível, mas não identifica uma pessoa
real. A API não deve ser exposta fora do ambiente local até autenticação e autorização serem
implementadas.

## Uso no painel demonstrativo

Na ficha do sinal, o analista escolhe explicitamente a sugestão de agrupamento ou prioridade e a
ação de aceitar, corrigir ou rejeitar. Correção e rejeição exigem motivo estruturado; correção
também exige campo e valor propostos. A mudança de etapa usa as transições declaradas acima e o
encerramento exige motivo. Antes da submissão, o painel pede confirmação.

Cada submissão gera uma `operation_key` e desabilita novos envios enquanto estiver pendente. A
resposta bem-sucedida atualiza imediatamente estado, versão, data e histórico exibidos. Em `409`,
o painel explica a concorrência e permite recarregar os dados canônicos sem apagar o formulário.
O navegador fala apenas com rotas do Next; elas não aceitam nem encaminham a identidade do ator.

## Erros esperados

- `404 workflow_signal_not_found`: sinal inexistente;
- `409 invalid_workflow_transition`: transição não permitida;
- `409 workflow_version_conflict`: versão concorrente;
- `422 operation_key_conflict`: chave reutilizada com outro conteúdo;
- `422 review_target_not_found`: alvo não pertence ao sinal ou à versão indicada;
- `422 closure_reason_required` ou `reason_code_required`: justificativa obrigatória ausente.

