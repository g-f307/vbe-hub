# Documentação do VBE Hub

Voltar ao [contexto do projeto](../AGENTS.md).

## Ordem de leitura

1. [Requisitos e escopo](requirements.md)
2. [Arquitetura](architecture.md)
3. [Contrato de dados sintéticos](synthetic-data-contract.md)
4. [Contrato de normalização](normalization-contract.md)
5. [Contratos de provedores de IA](ai-provider-contracts.md)
6. [Contrato da ficha técnica](technical-sheet-contract.md)
7. [Protocolo de avaliação da ficha](technical-sheet-evaluation.md)
8. [Linha de base Gemini de 29/09/2026](technical-sheet-baseline-2026-09-29.md)
9. [Indexação semântica](semantic-indexing.md)
10. [Seleção de pares candidatos](candidate-selection.md)
11. [Classificação das relações](relation-classification.md)
12. [Avaliação da correlação](correlation-evaluation.md)
13. [Validação da correlação para profissionais de saúde](health-stakeholder-validation.md)
14. [Consolidação de sinais de alerta](signal-consolidation.md)
15. [Prioridade sugerida e explicável](suggested-priority.md)
16. [Revisão humana e trilha de auditoria](human-review-workflow.md)
17. [Avaliação dos agrupamentos e da revisão](grouping-evaluation.md)
18. [Consulta canônica de sinais para o painel](signal-read-api.md)
19. [Métricas operacionais e evidências sintéticas](operational-metrics-api.md)
20. [Geração e importação de dados sintéticos](synthetic-data-generation.md)
21. [Modelo persistente inicial](data-model.md)
22. [Fundação do frontend](frontend.md)
23. [Plano de implementação](implementation-plan.md)
24. [Execução e validação local](development.md)
25. [Integração contínua](continuous-integration.md)
26. [Decisões arquiteturais](decisions/README.md)

## Situação

Fundação reproduzível, normalização, extração, indexação semântica, funil de correlação,
consolidação auditável, prioridade sugerida por regras e fluxo de revisão humana implementados e
avaliados com dados sintéticos. Correlação e agrupamento foram aprovados com ressalvas. A API e as
rotas de triagem, investigação e panorama usam leitura canônica; a investigação também registra
decisões auditáveis por rotas internas do painel. O backend expõe métricas operacionais
reconciliáveis separadas das avaliações sintéticas. Autenticação institucional e integrações reais
com EIOS e Guardiões da Saúde permanecem
nas etapas seguintes; os contratos atuais simulam as entradas sem afirmar equivalência com
endpoints oficiais.
