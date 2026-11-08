---
id: ADR-002
type: adr
status: active
title: "ADR-002: Isolar provedores de IA"
created: 2026-09-28
updated: 2026-11-08
owner: VBE Hub
related_docs:
  - DES-001
---

# ADR-002: Isolar provedores de IA

## Status

Aceita em 2026-09-28 e atualizada em 2026-11-08 pela decisão operacional da ADR-010.

## Contexto

A PoC precisa de extração estruturada, embeddings e julgamento de relações. Gemini oferece saída estruturada e embeddings por API. Ollama pode permitir experimentos locais, mas a GPU de 4 GB limita modelos generativos maiores.

## Decisão

Definir portas na camada de aplicação para extração, embeddings e julgamento de relação. Manter os
tipos de domínio e os casos de uso sem imports de SDKs. A inclusão de um provedor em uma porta não
implica acoplá-lo ao domínio nem torná-lo permanente.

Gemini permanece como implementação e evidência histórica da fase inicial; Ollama permanece apenas
como possibilidade experimental. Conforme a ADR-010, OpenAI será o único provedor externo do
caminho operacional oficial da PoC após a migração das issues #69 a #77. Testes continuam usando
doubles determinísticos e a demonstração pode usar respostas previamente registradas, claramente
identificadas como fallback.

## Alternativas consideradas

- Acoplar todo o domínio a Gemini: reduz o trabalho imediato, mas dificulta teste local e mudança de fornecedor.
- Usar somente Ollama: reduz chamadas externas, mas cria risco de qualidade e latência no hardware disponível.

## Consequências

O código terá pequenos adapters adicionais. Em troca, testes usam um provedor falso determinístico
e uma suíte de contrato reutilizável. Erros atravessam essa fronteira apenas em categorias neutras
e com mensagens sanitizadas. A configuração oficial ficará mais simples ao depender de uma única
API externa, sem apagar resultados comparativos anteriores. Até a conclusão da migração, partes do
código ainda podem conter adapters Gemini; presença no repositório não significa uso operacional.
