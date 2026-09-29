---
id: API-004
type: api
status: active
title: Contrato da ficha técnica extraída
created: 2026-09-29
updated: 2026-09-29
owner: VBE Hub
implemented_code:
  - backend/src/vbe_hub/application/ai/technical_sheet.py
  - backend/src/vbe_hub/application/ai/assets/
  - backend/src/vbe_hub/adapters/ai/gemini.py
related_docs:
  - API-002
  - API-003
  - DATA-001
  - ADR-002
---

# Contrato da ficha técnica extraída

Voltar ao [índice da documentação](README.md).

## Finalidade e versões

A ficha transforma um registro normalizado em atributos comparáveis para etapas posteriores de
busca e correlação. Ela não representa diagnóstico, confirmação de surto, prioridade definitiva
ou decisão sanitária.

- schema: `technical-sheet-v1`;
- prompt: `extract-v1`;
- JSON Schema versionado: `backend/src/vbe_hub/application/ai/assets/technical-sheet-v1.schema.json`;
- prompt versionado: `backend/src/vbe_hub/application/ai/assets/extract-v1.prompt.txt`.

O teste de contrato exige que o arquivo JSON Schema permaneça idêntico ao schema produzido pelo
modelo Pydantic. Mudanças incompatíveis exigem nova versão, sem editar silenciosamente a versão
já usada em experimentos.

## Campos

| Grupo | Campos | Regra principal |
| --- | --- | --- |
| classificação | natureza, doença/agravo, patógeno, síndrome | Escalares sem suporte ficam `null`. |
| manifestação | sintomas | Lista vazia quando ausente. |
| magnitude | casos e óbitos estimados | Inteiros não negativos ou `null`. |
| contexto | grupo afetado, ambiente, ação em andamento | Texto apoiado por evidência ou `null`. |
| tempo | início, fim e precisão | Datas ISO ou `null`; precisão é enumerada. |
| lugar | país, estado, município, bairro/distrito, local e precisão | Componentes ausentes ficam `null`. |
| sugestão | relevância e confiança da extração | Relevância baixa/moderada/alta; confiança entre 0 e 1. |
| explicação | evidências por campo | Trechos literais de até 240 caracteres da entrada normalizada. |

Todo atributo extraído não nulo precisa de evidência. A confiança mede apenas a confiança da
extração e não substitui evidência. Campos desconhecidos são rejeitados.

## Validação e segurança

O registro normalizado é serializado de forma determinística e delimitado como conteúdo não
confiável. O prompt instrui o modelo a não obedecer comandos encontrados dentro do registro. O
adapter não fornece ferramentas, busca, execução de código, shell, SQL ou capacidade de alterar
estado.

O Gemini recebe o JSON Schema como formato obrigatório, mas a resposta continua não confiável.
Antes da persistência, a aplicação repete localmente a validação de tipos, enums, limites, campos
extras, nulos e evidências literais. Resposta inválida vira falha estruturada e nunca entra como
ficha válida.

## Cache e auditoria

A chave SHA-256 do cache inclui:

- hash da entrada;
- provedor;
- modelo;
- versão do prompt;
- versão do schema.

Repetir a mesma configuração reutiliza a ficha sem nova chamada. Alterar qualquer componente
invalida a chave. A tabela `technical_sheet_extractions` mantém no máximo uma linha por chave e
registra sucesso ou última falha, ficha, evidências, modelo, versões, início, duração, unidades,
erro sanitizado e repetibilidade. Uma falha transitória pode ser substituída pelo sucesso da
mesma chave, sem duplicar a ficha.

## Gemini

O adapter usa o SDK oficial `google-genai` e a API estável `v1`. O modelo é configurável; o valor
inicial em 29 de setembro de 2026 é `gemini-3.5-flash-lite`, modelo estável indicado para extração
de documentos com menor custo. O modelo não é parte do domínio e pode ser alterado para o
experimento sem mudança de código.

O SDK tem seu retry interno desabilitado. A aplicação limita tentativas, timeout, caracteres de
entrada e tokens de saída, e aplica backoff somente para timeout, rate limit e indisponibilidade.
Detalhes atuais devem ser confirmados na [documentação de modelos](https://ai.google.dev/gemini-api/docs/models),
na [saída estruturada](https://ai.google.dev/gemini-api/docs/structured-output), nos
[limites](https://ai.google.dev/gemini-api/docs/rate-limits) e nos
[preços](https://ai.google.dev/gemini-api/docs/pricing) antes de cada experimento.
