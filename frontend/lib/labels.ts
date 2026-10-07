import type { RelationKind, SourceType, SuggestedPriority, WorkflowState } from './types'

export const WORKFLOW_ORDER: WorkflowState[] = [
  'detectado',
  'triagem',
  'verificacao',
  'avaliacao_risco',
  'encerrado',
]

export const WORKFLOW_LABEL: Record<WorkflowState, string> = {
  detectado: 'Detectado',
  triagem: 'Triagem',
  verificacao: 'Verificação',
  avaliacao_risco: 'Avaliação de risco',
  encerrado: 'Encerrado',
}

export const WORKFLOW_QUEUE_LABEL: Record<WorkflowState, string> = {
  detectado: 'Detectado',
  triagem: 'Aguardando triagem',
  verificacao: 'Em verificação',
  avaliacao_risco: 'Em avaliação de risco',
  encerrado: 'Encerrado',
}

export const VALID_TRANSITIONS: Record<WorkflowState, WorkflowState[]> = {
  detectado: ['triagem', 'encerrado'],
  triagem: ['verificacao', 'encerrado'],
  verificacao: ['avaliacao_risco', 'encerrado'],
  avaliacao_risco: ['encerrado'],
  encerrado: [],
}

export const PRIORITY_LABEL: Record<SuggestedPriority, string> = {
  urgente: 'Urgente',
  atencao: 'Atenção',
  monitorar: 'Monitorar',
  contexto: 'Contexto',
}

export const PRIORITY_DESCRIPTION: Record<SuggestedPriority, string> = {
  urgente: 'Múltiplas fontes independentes, magnitude crescente ou condição de alto impacto.',
  atencao: 'Fontes convergentes que justificam triagem no mesmo turno.',
  monitorar: 'Poucas fontes ou magnitude baixa; acompanhar novas menções.',
  contexto: 'Informação de apoio, sem indicação de evento em curso.',
}

export const SOURCE_TYPE_LABEL: Record<SourceType, string> = {
  midia: 'Mídia',
  comunidade: 'Comunidade',
}

export const RELATION_LABEL: Record<RelationKind, string> = {
  corroboracao: 'Corroboração sugerida',
  atualizacao: 'Atualização sugerida',
  contexto: 'Contexto, não evidência central',
  divergencia: 'Divergência sugerida',
}

export const REJECTION_REASONS = [
  { value: 'eventos_diferentes', label: 'Eventos diferentes' },
  { value: 'evidencia_insuficiente', label: 'Evidência insuficiente' },
  { value: 'incompatibilidade_geografica', label: 'Incompatibilidade geográfica' },
  { value: 'incompatibilidade_temporal', label: 'Incompatibilidade temporal' },
  { value: 'outro', label: 'Outro' },
] as const

export const CLOSE_REASONS = [
  { value: 'sem_evento', label: 'Sem indicação de evento após triagem' },
  { value: 'ja_acompanhado', label: 'Evento já acompanhado por outro sinal' },
  { value: 'duplicado', label: 'Registro duplicado' },
  { value: 'apenas_contexto', label: 'Apenas informação de contexto' },
] as const
