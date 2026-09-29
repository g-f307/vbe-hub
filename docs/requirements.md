---
id: REQ-001
type: requirements
status: active
title: Requisitos e escopo
created: 2026-09-28
updated: 2026-09-28
owner: VBE Hub
related_docs:
  - DES-001
  - API-001
  - REL-001
  - ADR-004
---

# Requisitos e escopo

## Objetivo

Demonstrar uma prova de conceito que recebe registros sintéticos equivalentes, em nível semântico, a notícias de saúde e relatos comunitários; extrai uma ficha técnica; identifica relações entre registros; e apresenta sinais consolidados para revisão humana.

## Dentro do escopo da validação

- Geração em massa de dados sintéticos, com proveniência e rótulos conhecidos.
- Normalização dos formatos de entrada em um registro comum.
- Extração estruturada por IA de doença/síndrome, sintomas, tempo, lugar, magnitude e contexto.
- Correlação de registros como duplicata, corroboração, atualização, contexto relacionado ou sem relação.
- Agrupamento, prioridade sugerida explicável e painel de revisão.
- Métricas de qualidade e de desempenho sobre um conjunto de referência rotulado.

## Fora do escopo da validação

- Consumo de APIs reais do EIOS ou Guardiões da Saúde.
- Diagnóstico, confirmação de surto, notificação oficial ou resposta de saúde pública.
- Armazenamento de dados pessoais, identificáveis ou clínicos individuais.

## Requisito de reprodutibilidade por Docker

Docker Compose é a interface oficial de execução, teste e demonstração da PoC. A validação em outro dispositivo deve exigir somente Git, Docker e Docker Compose no host.

Ao final da etapa 1, o repositório deve fornecer:

- imagens construídas a partir de Dockerfiles versionados;
- composição local com API, PostgreSQL/pgvector e Redis;
- `.env.example` sem credenciais reais;
- migrations executáveis em contêiner;
- geração e importação de um lote sintético por comando em contêiner;
- health checks com espera explícita pelas dependências;
- volumes e política de limpeza documentados;
- comandos equivalentes para inicialização, testes, lint e auditoria;
- versões de imagens e dependências fixadas de forma reproduzível.

A máquina hospedeira não pode precisar de Python, Node.js, PostgreSQL, Redis, Gemini CLI ou Ollama para executar o caminho oficial de validação. Serviços externos opcionais, como Gemini, devem possuir configuração explícita e um modo de demonstração que não exponha segredos.

### Critérios de aceite da etapa 1

- Um clone limpo inicia a base da aplicação pelos comandos documentados.
- A composição constrói as imagens sem depender de arquivos não versionados, exceto `.env` criado a partir do exemplo.
- API, PostgreSQL/pgvector e Redis atingem estado saudável de forma observável.
- Migrations, testes e geração/importação sintética rodam dentro dos contêineres.
- A mesma semente gera o mesmo manifesto e conjunto sintético esperado.
- A CI executa o caminho Docker em ambiente limpo.
- Falhas de configuração ou dependência retornam erro claro e status diferente de zero.
- Nenhum segredo, dado pessoal, cache ou volume local é versionado.

## Critérios de aceite da macroentrega 1

- Importar um lote sintético reprodutível e processar todos os registros sem intervenção manual.
- Exibir, para cada registro, texto de origem, ficha técnica extraída, confiança e origem sintética.
- Exibir, para cada sinal consolidado, fontes vinculadas, relação entre registros, justificativa, prioridade sugerida e status do fluxo.
- Permitir ao avaliador aceitar, corrigir ou rejeitar a sugestão de relação/agrupamento.
- Gerar relatório com precisão, revocação, F1, falsos positivos e tempo de processamento.

## Fundamentação operacional

O fluxo implementado seguirá a separação proposta pelo Africa CDC: detecção, triagem, verificação, avaliação de risco e alerta/resposta. A PoC automatiza detecção, pré-triagem e sugestão de correlação; verificação e avaliação de risco permanecem humanas.
