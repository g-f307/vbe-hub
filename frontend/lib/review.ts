import { CLOSE_REASONS, REJECTION_REASONS, VALID_TRANSITIONS, WORKFLOW_LABEL } from './labels'
import type { NextStep, ReviewDecisionType, WorkflowState } from './types'

export const DECISION_LABEL: Record<ReviewDecisionType, string> = {
  aceitar: 'Aceitar agrupamento',
  corrigir: 'Corrigir agrupamento',
  rejeitar: 'Rejeitar agrupamento',
}

export const DECISION_PAST_LABEL: Record<ReviewDecisionType, string> = {
  aceitar: 'Agrupamento aceito',
  corrigir: 'Agrupamento corrigido',
  rejeitar: 'Agrupamento rejeitado',
}

export function nextActiveState(state: WorkflowState): WorkflowState | undefined {
  return VALID_TRANSITIONS[state].find((s) => s !== 'encerrado')
}

export function resolveResultingState(current: WorkflowState, step: NextStep): WorkflowState {
  if (step === 'encerrar') return 'encerrado'
  if (step === 'avancar') return nextActiveState(current) ?? current
  return current
}

export function nextStepLabel(current: WorkflowState, step: NextStep) {
  if (step === 'encerrar') return 'Encerrar sinal'
  if (step === 'avancar') {
    const next = nextActiveState(current)
    return next ? `Mover para ${WORKFLOW_LABEL[next].toLowerCase()}` : 'Avançar'
  }
  return `Manter em ${WORKFLOW_LABEL[current].toLowerCase()}`
}

export function rejectionReasonLabel(value?: string) {
  return REJECTION_REASONS.find((r) => r.value === value)?.label
}

export function closeReasonLabel(value?: string) {
  return CLOSE_REASONS.find((r) => r.value === value)?.label
}
