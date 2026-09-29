---
id: REL-001
type: release
status: active
title: Plano de implementação
created: 2026-09-28
updated: 2026-09-28
owner: VBE Hub
review_after: 2026-11-07
related_docs:
  - REQ-001
  - DES-001
  - API-001
  - ADR-004
---

# Plano de implementação

## Marco de validação

Meta: demonstração validável até **7 de novembro de 2026**, com janela preferencial entre o fim de outubro e o início de novembro.

| Período | Entrega | Evidência de conclusão |
| --- | --- | --- |
| 28 set - 4 out | Fundação do projeto | Banco local, contrato sintético, gerador determinístico e importação de lote. |
| 5 - 11 out | Normalização e ficha técnica | JSON validado, persistência, tratamento de nulos e amostras revisadas manualmente. |
| 12 - 18 out | Candidatos e correlação | Busca vetorial, filtros espaço-temporais e relações entre pares. |
| 19 - 25 out | Agrupamento e revisão | Sinais consolidados, justificativa, prioridade sugerida e revisão humana. |
| 26 out - 1 nov | Painel e métricas | Painel mínimo e relatório automático de precisão, revocação, F1 e tempo. |
| 2 - 7 nov | Validação e apresentação | Experimento reproduzível, correções e roteiro de demonstração. |

## Etapa 1: fundação reproduzível

A primeira etapa termina somente quando um clone limpo puder ser validado via Docker. A entrega não é apenas a existência de Dockerfiles.

### Entregáveis

- Estrutura do monólito modular e imagem do backend.
- PostgreSQL com pgvector e Redis em versões fixadas.
- Health checks e configuração segura por `.env.example`.
- Migrations e persistência inicial.
- Gerador determinístico, gabarito separado e importador sintético.
- Suíte de validação do dataset.
- CI com lint, testes, migrations e smoke test da composição.
- README com comandos efetivamente executados.

### Fluxo de validação esperado

1. Clonar o repositório e criar `.env` a partir do exemplo.
2. Construir e iniciar a composição.
3. Aguardar health checks e aplicar migrations pelo fluxo documentado.
4. Gerar/importar um lote pequeno com semente fixa.
5. Consultar o health check e confirmar as contagens persistidas.
6. Executar testes, lint e validação sintética dentro dos contêineres.
7. Encerrar sem apagar dados por padrão; disponibilizar reset explícito e documentado.

### Evidência de conclusão

- Execução em ambiente limpo ou runner da CI.
- Logs sanitizados dos health checks, migrations e importação.
- Manifesto e hash do lote sintético.
- Resultado dos testes e smoke test Docker.
- Confirmação de que nenhum runtime da aplicação foi usado diretamente no host.

## Ordem de construção

1. Criar o dataset de referência antes de calibrar prompts ou limiares.
2. Construir o domínio e os testes com um provedor de IA simulado.
3. Adicionar Gemini e registrar custo, latência e qualidade.
4. Testar Ollama como experimento comparativo, sem tornar a PoC dependente da GPU local.
5. Implementar o painel apenas quando o pipeline gerar sinais auditáveis.

## Riscos e respostas

| Risco | Resposta |
| --- | --- |
| Lote grande exceder limite/cota de IA | Processar em lote, armazenar cache por hash e limitar julgamentos de pares. |
| IA inventar atributos clínicos | Schema estrito, campo de evidência, nulos explícitos e revisão amostral. |
| Agrupamentos excessivos | Separar duplicata, corroboração e contexto; medir falsos positivos. |
| Ollama ser lento ou insuficiente | Usá-lo apenas como baseline local e manter o adapter Gemini. |
| Formato real divergir do sintético | Manter contratos de fonte separados e normalização como fronteira estável. |
