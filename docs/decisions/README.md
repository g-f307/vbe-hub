# Decisões arquiteturais

Voltar à [documentação](../README.md).

| Decisão | Estado | Assunto |
| --- | --- | --- |
| [ADR-001](ADR-001-modular-monolith.md) | Aceita | Monólito modular para a PoC. |
| [ADR-002](ADR-002-pluggable-ai.md) | Aceita, atualizada | Portas intercambiáveis; OpenAI como único provedor operacional futuro da PoC. |
| [ADR-003](ADR-003-synthetic-data.md) | Aceita | Dados sintéticos rotulados até a validação. |
| [ADR-004](ADR-004-docker-reproducibility.md) | Aceita | Docker Compose como interface oficial de reprodução e validação. |
| [ADR-005](ADR-005-sqlalchemy-alembic.md) | Aceita | SQLAlchemy e Alembic isolados do domínio. |
| [ADR-006](ADR-006-versioned-signal-consolidation.md) | Substituída | Consolidação automática preservada como decisão e comportamento legados. |
| [ADR-007](ADR-007-rules-based-suggested-priority.md) | Aceita, parcialmente substituída | Regras explicáveis preservadas; prioridade futura pertence à ficha. |
| [ADR-008](ADR-008-append-only-human-review.md) | Aceita | Decisões humanas como eventos imutáveis e concorrentes. |
| [ADR-009](ADR-009-n8n-demo-orchestration.md) | Aceita | n8n restrito à orquestração visual da demonstração sintética. |
| [ADR-010](ADR-010-individual-signals-human-investigation.md) | Aceita, parcialmente substituída | Cada fonte é um sinal; a IA sugere relações e o analista forma fichas. |
| [ADR-011](ADR-011-head-signal-evidence.md) | Aceita | A investigação mantém um sinal-cabeça e os demais membros como evidências auditáveis. |
