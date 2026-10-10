---
id: REL-001
type: release
status: active
title: Plano de implementação
created: 2026-09-28
updated: 2026-10-07
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

## Etapa 5: painel do analista e integração do frontend

O mockup exploratório definiu a direção visual, os componentes de evidência e os percursos de
triagem, investigação e panorama. A fundação resultante já está em `frontend/`, executa por Docker
Compose e preserva a exportação original como artefato local ignorado. Triagem e investigação
possuem vínculo de leitura com o backend e exibem dados sintéticos persistidos; o panorama ainda
aguarda integração própria.

### Ordem de implementação

1. **Concluída em 7 de outubro:** criar a aplicação Next.js/React em `frontend/`, sua imagem Docker
   e os comandos Compose de desenvolvimento, demonstração, testes e build. A entrega incorporou os
   componentes e rotas do export v0 com dados mockados, sem recriar uma interface paralela.
2. Expor contrato de leitura de fila e detalhe a partir de dados sintéticos persistidos, preservando
   fontes, ficha, relações, divergências, prioridade e auditoria. O contrato não materializa
   workflow durante uma leitura.
3. **Concluída:** conectar as rotas v0 de triagem e investigação a esse contrato, mantendo o
   desenho, a responsividade e os estados de carregamento, vazio, falha e 404; os mocks não
   alimentam essas duas rotas, mas podem permanecer em páginas ainda não integradas ou testes de componente.
4. Integrar a decisão humana auditável: aceitar, corrigir e rejeitar agrupamento, com controle de
   versão e comunicação clara de sucesso, conflito ou erro.
5. Integrar o panorama operacional e a visualização geoespacial agregada por área, sem localização
   individual ou dependência de tile externo para a demonstração.
6. Acrescentar Kanban como visão complementar de acompanhamento do fluxo, sem transição de estado
   por arrastar e soltar fora do fluxo de revisão.
7. Validar responsividade, acessibilidade, dados sintéticos, limites da IA e reprodução completa
   em outro dispositivo via Docker Compose.

### Critérios de aceite do painel integrado

- Triagem apresenta paginação, filtros e cartões/linhas com hierarquia de informação para lotes
  volumosos; detalhe preserva fontes, fichas, divergências e justificativa.
- Todo estado exibido vem da API ou é explicitamente uma simulação de demonstração; a interface não
  confirma doença, surto ou prioridade final.
- Revisão humana respeita transições válidas, concorrência otimista e trilha append-only.
- Mapa mostra somente agregados aprovados de área e direciona a uma fila filtrada; funciona em
  modo de demonstração sem Internet.
- Kanban e tabela representam o mesmo estado canônico e apresentam transições como ações
  auditáveis, não como automação sanitária.
- Clone limpo inicia backend e frontend pelo Docker Compose documentado, sem Node.js instalado no
  host.

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

A etapa de agrupamento e revisão foi concluída antecipadamente em 7 de outubro de 2026 com uma
avaliação sintética ampliada. A aprovação possui ressalvas e não antecipa a validação integrada da
Etapa 6 nem a interface da Etapa 5.

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
