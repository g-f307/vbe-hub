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
   - [Análise e correção da extração em 28/10/2026](technical-sheet-remediation-2026-10-28.md)
   - [Avaliação exploratória OpenAI em 04/11/2026](openai-technical-sheet-evaluation-2026-11-04.md)
10. [Seleção de pares candidatos](candidate-selection.md)
11. [Classificação das relações](relation-classification.md)
12. [Avaliação da correlação](correlation-evaluation.md)
13. [Validação da correlação para profissionais de saúde](health-stakeholder-validation.md)
14. [Transição para sinais individuais e fichas de investigação](signal-domain-transition.md)
15. [Persistência de sinais individuais e fichas](individual-signal-persistence.md)
   - [API versionada de sinais individuais e fichas](individual-signal-api.md)
16. [Consolidação de sinais de alerta — legado](signal-consolidation.md)
   - [Pré-cálculo assíncrono de sinais relacionados](related-signal-precomputation.md)
17. [Prioridade sugerida e explicável](suggested-priority.md)
18. [Revisão humana e trilha de auditoria](human-review-workflow.md)
19. [Avaliação dos agrupamentos e da revisão](grouping-evaluation.md)
20. [Consulta canônica de sinais para o painel](signal-read-api.md)
21. [Métricas operacionais e evidências sintéticas](operational-metrics-api.md)
22. [Experimento integrado da prova de conceito](integrated-validation.md)
23. [Geração e importação de dados sintéticos](synthetic-data-generation.md)
24. [Modelo persistente inicial](data-model.md)
25. [Fundação do frontend](frontend.md)
26. [Plano de implementação](implementation-plan.md)
27. [Demonstração visual com fontes dispersas no n8n](n8n-demo.md)
28. [Execução e validação local](development.md)
29. [Integração contínua](continuous-integration.md)
30. [Decisões arquiteturais](decisions/README.md)

## Situação

O comportamento consolidado permanece reproduzível como evidência histórica. Em 2026-11-08, a
ADR-010 aprovou a transição para um sinal individual por fonte, sugestões pré-calculadas pela
OpenAI e fichas formadas somente por decisão humana. Persistência, worker assíncrono e API `/v1`
estão implementados sem retirar o modelo legado. O workflow completo e a interface ainda serão
migrados pelo caminho expand/contract descrito em [Transição para sinais
individuais](signal-domain-transition.md).

Autenticação institucional e integrações reais com EIOS e Guardiões da Saúde permanecem fora da
PoC; os contratos simulam entradas sem afirmar equivalência com endpoints oficiais.
