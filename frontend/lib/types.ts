export type UUID = string

export type WorkflowState =
  | 'detectado'
  | 'triagem'
  | 'verificacao'
  | 'avaliacao_risco'
  | 'encerrado'

export type SuggestedPriority = 'urgente' | 'atencao' | 'monitorar' | 'contexto'

export type SourceType = 'midia' | 'comunidade'

export type RelationKind = 'corroboracao' | 'atualizacao' | 'contexto' | 'divergencia'

export interface RelationSuggestion {
  kind: RelationKind
  label: string
  confidence: number
  rationale: string
}

export interface TechnicalSheet {
  condition: string | null
  symptoms: string[]
  location: string | null
  period: string | null
  magnitude: string | null
  missingFields: string[]
  extractionVersion: string
  extractedAt: string
}

export interface SourceRecord {
  id: UUID
  code: string
  signalId: UUID
  type: SourceType
  subtype: string
  title: string
  excerpt: string
  origin: string
  publishedAt: string
  municipality: string
  neighborhood: string
  isContext: boolean
  relation: RelationSuggestion
  sheet: TechnicalSheet
}

export interface GroupingCriterion {
  label: string
  detail: string
  met: boolean
}

export interface Signal {
  id: UUID
  code: string
  slug: string
  title: string
  subtitle: string
  condition: string
  symptoms: string[]
  municipality: string
  neighborhood: string
  periodStart: string
  periodEnd: string
  magnitude: string | null
  priority: SuggestedPriority
  priorityRationale: string
  state: WorkflowState
  createdAt: string
  updatedAt: string
  sourceIds: UUID[]
  criteria: GroupingCriterion[]
  divergences: string[]
  flag?: 'conflito_geografico' | 'condicao_desconhecida' | 'contexto'
}

export type ReviewDecisionType = 'aceitar' | 'corrigir' | 'rejeitar'

export type NextStep = 'manter' | 'avancar' | 'encerrar'

export interface ReviewDecision {
  id: UUID
  signalId: UUID
  type: ReviewDecisionType
  removedSourceIds: UUID[]
  correctionReason?: string
  rejectionReason?: string
  comment?: string
  nextStep: NextStep
  closeReason?: string
  resultingState: WorkflowState
  decidedAt: string
  decidedBy: string
}

export type AuditActor = 'sistema' | 'analista'

export interface AuditEvent {
  id: UUID
  signalId: UUID
  at: string
  actor: AuditActor
  title: string
  description: string
  pending?: boolean
}

export interface PipelineMetric {
  key: string
  label: string
  value: string
  description: string
  tone?: 'neutro' | 'atencao' | 'erro'
}

export interface QueueIndicator {
  key: WorkflowState | 'conflito'
  label: string
  value: number
  trend: 'up' | 'down' | 'flat'
  trendLabel: string
}

export interface NeighborhoodSummary {
  id: string
  name: string
  x: number
  y: number
  signals: number
  media: number
  community: number
  conditions: { label: string; count: number }[]
  states: { state: WorkflowState; count: number }[]
  dominantState: WorkflowState
}
