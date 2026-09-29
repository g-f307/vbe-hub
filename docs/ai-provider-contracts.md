---
id: API-003
type: api
status: active
title: Contratos de provedores de inteligência artificial
created: 2026-09-29
updated: 2026-09-29
owner: VBE Hub
implemented_code:
  - backend/src/vbe_hub/application/ai/
  - backend/src/vbe_hub/adapters/ai/fake.py
related_docs:
  - DES-001
  - ADR-002
---

# Contratos de provedores de inteligência artificial

Voltar ao [índice da documentação](README.md).

## Objetivo e limite

A aplicação expõe três portas assíncronas e independentes de SDK: `StructuredExtractor`,
`EmbeddingProvider` e `RelationJudge`. Implementações Gemini, Ollama ou futuras pertencem à
camada de adapters; os casos de uso devem depender apenas desses contratos.

Nesta etapa, o resultado da IA é uma sugestão auditável. Os contratos não confirmam eventos,
não definem prioridade sanitária, não consolidam sinais e não recebem os rótulos `gold` usados
na avaliação experimental.

## Portas

| Porta | Entrada | Saída validada |
| --- | --- | --- |
| `StructuredExtractor` | registro normalizado, identificadores de registro/hash/rastreio e versões de schema/prompt | ficha técnica genérica, evidências por campo e metadata de execução |
| `EmbeddingProvider` | texto preparado, ID estável, hash e dimensão esperada | vetor finito com dimensão conferida e metadata de execução |
| `RelationJudge` | dois candidatos distintos, versões e rastreio | relação enumerada, justificativa de até 500 caracteres, confiança entre 0 e 1 e metadata |

A estrutura definitiva da ficha técnica será definida na issue #8. Por isso, o contrato atual
transporta um mapa validado pelo adapter, sem antecipar campos clínicos ainda em estudo.

## Relações sugeridas

- `duplicate`: duas representações do mesmo relato ou conteúdo;
- `corroborates`: fontes diferentes oferecem evidências compatíveis;
- `updates`: um registro acrescenta evolução temporal a outro;
- `related_context`: há contexto comum, sem corroboração suficiente;
- `unrelated`: não há relação relevante identificada.

Essa enumeração descreve a relação proposta pelo modelo, não uma decisão humana.

## Metadata e falhas

Toda execução bem-sucedida registra provedor, modelo, versões do contrato e do prompt quando
aplicável, início com fuso horário, duração, unidades de entrada/saída e uso de cache. Falhas
usam `ProviderError`, com mensagem sanitizada, indicação de repetibilidade e uma das categorias:

- configuração ausente ou inválida;
- tempo limite;
- limite de requisições ou cota;
- resposta inválida;
- indisponibilidade temporária;
- falha permanente não classificada.

Adapters não devem propagar respostas brutas, credenciais, prompts completos ou detalhes
internos do fornecedor. Timeouts, cotas e limites de consumo serão configurados no adapter real.

## Fronteiras de confiança

Texto de mídia/comunidade e toda saída do modelo são não confiáveis. O modelo não recebe
ferramentas para executar shell, SQL, HTTP ou alterações de estado. Uma implementação real deve
usar saída estruturada, validar o resultado contra o contrato e impedir que texto gerado alcance
diretamente um sink executável. Prompts não podem conter segredos nem regras de autorização.

Essas restrições reduzem os riscos de prompt injection, consumo sem limite e tratamento
inadequado de saída; elas não tornam o conteúdo do modelo verdadeiro. Evidências e confiança
devem permanecer visíveis para revisão profissional.

## Provider falso e testes de substituição

O adapter falso é offline e determinístico: recebe um instante fixo, deriva respostas de IDs ou
hashes, aceita dimensão configurável para embeddings e simula falhas por hash. Ele não consulta
rede, relógio, aleatoriedade nem variáveis secretas.

Os testes reutilizáveis em `backend/tests/contracts/ai.py` verificam determinismo, metadata,
dimensão, evidência e limites de confiança. Cada novo adapter deverá executar esses contratos,
além de testes específicos do fornecedor.
