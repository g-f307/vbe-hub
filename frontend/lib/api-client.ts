import type {
  AuditEvent,
  NeighborhoodSummary,
  PipelineMetric,
  ReviewDecision,
  Signal,
  SourceRecord,
  SuggestedPriority,
  WorkflowState,
} from './types'

/**
 * Contrato preparado para a futura API FastAPI do VBE Hub.
 * Nesta versão nenhuma chamada de rede é realizada; a interface documenta
 * os endpoints esperados para que a integração substitua os mocks locais.
 */

export interface SignalQueueFilters {
  search?: string
  state?: WorkflowState
  priority?: SuggestedPriority
  neighborhood?: string
  sourceType?: 'midia' | 'comunidade'
  periodDays?: number
  page?: number
  pageSize?: number
}

export interface Paginated<T> {
  items: T[]
  total: number
  page: number
  pageSize: number
}

export interface SignalDetail {
  signal: Signal
  sources: SourceRecord[]
  audit: AuditEvent[]
}

export type ReviewDecisionInput = Omit<ReviewDecision, 'id' | 'decidedAt' | 'resultingState'>

export interface VbeApiClient {
  /** GET /sinais */
  listSignals(filters: SignalQueueFilters): Promise<Paginated<Signal>>
  /** GET /sinais/{codigo} */
  getSignal(code: string): Promise<SignalDetail>
  /** POST /sinais/{codigo}/decisoes */
  submitDecision(code: string, decision: ReviewDecisionInput): Promise<ReviewDecision>
  /** GET /panorama/bairros */
  getNeighborhoodSummary(periodDays: number): Promise<NeighborhoodSummary[]>
  /** GET /pipeline/metricas */
  getPipelineMetrics(): Promise<PipelineMetric[]>
}

export const API_BASE_URL_ENV = 'NEXT_PUBLIC_VBE_API_URL'

/**
 * A base da futura API vem exclusivamente da configuração de implantação.
 * Como a variável é exposta ao navegador, credenciais não são aceitas.
 */
export function resolveApiBaseUrl(rawValue = process.env[API_BASE_URL_ENV]): string {
  const configuredValue = rawValue?.trim() || 'http://localhost:8000'

  let url: URL
  try {
    url = new URL(configuredValue)
  } catch {
    throw new Error('A URL pública da API é inválida.')
  }

  if (url.protocol !== 'http:' && url.protocol !== 'https:') {
    throw new Error('A URL pública da API deve usar HTTP ou HTTPS.')
  }

  if (url.username || url.password) {
    throw new Error('A URL pública da API não pode conter credenciais.')
  }

  if (url.search || url.hash) {
    throw new Error('A URL pública da API não pode conter parâmetros ou fragmentos.')
  }

  return url.toString().replace(/\/$/, '')
}
