import type {
  AuditEvent,
  GroupingCriterion,
  RelationKind,
  Signal,
  SourceRecord,
  SuggestedPriority,
  TechnicalSheet,
  WorkflowState,
} from './types'

const INTERNAL_API_URL_ENV = 'VBE_API_INTERNAL_URL'
const DEFAULT_INTERNAL_API_URL = 'http://api:8000'
const PAGE_SIZE = 6

export type QueueFilters = {
  query?: string
  state?: WorkflowState | 'todos' | string
  priority?: SuggestedPriority | 'todas' | string
  district?: string
  sourceType?: string
  period?: '24h' | '7d' | '14d' | 'todos'
  page?: number
}

type ApiLocation = {
  country: string | null
  state: string | null
  municipality: string | null
  district: string | null
  precision: string | null
}

type ApiQueueSignal = {
  id: string
  title: string
  summary: string
  conditions: string[]
  symptoms: string[]
  period_start: string | null
  period_end: string | null
  location: ApiLocation
  source_counts: { media: number; community: number; total: number }
  priority: {
    id: string
    band: 'routine' | 'attention' | 'prompt'
    score: number
    confidence: number
    policy_version: string
    identity_key: string
  } | null
  workflow: {
    state: 'detected' | 'triage' | 'verification' | 'risk_assessment' | 'closed'
    version: number
    updated_at: string | null
  }
}

type ApiSource = {
  normalized_record_id: string
  role: string
  source_kind: 'media' | 'community'
  source_name: string
  published_at: string
  title: string | null
  excerpt: string
  technical_sheet: Record<string, unknown> | null
}

type ApiRelation = {
  id: string
  role: string
  relation: string | null
  confidence: number | null
  justification: string | null
  method: string
  state: string
}

type ApiAuditEvent = {
  id: string
  sequence: number
  workflow_version: number
  workflow_state: string
  actor_id: string
  occurred_at: string
  action: string
  target_type: string | null
  target_id: string
  previous_value: Record<string, unknown>
  new_value: Record<string, unknown>
  reason_code: string | null
  comment: string | null
}

type ApiSignalDetail = {
  signal: ApiQueueSignal
  grouping: {
    identity_key: string
    policy_version: string
    processing_state: string
    divergence_codes: string[]
  }
  sources: ApiSource[]
  relations: ApiRelation[]
  audit_events: ApiAuditEvent[]
}

export type SignalDetailView = {
  signal: Signal
  sources: SourceRecord[]
  criteria: GroupingCriterion[]
  audit: AuditEvent[]
  workflow: { state: WorkflowState; version: number; updatedAt: string | null }
  reviewTargets: ReviewTarget[]
}

export type ReviewTarget = {
  type: 'grouping' | 'priority'
  id: string
  suggestionIdentityKey: string
  label: string
}

export type SignalQueueView = {
  items: Signal[]
  page: number
  pageSize: number
  total: number
}

export class SignalReadError extends Error {
  constructor(
    message: string,
    readonly kind: 'unavailable' | 'invalid-response' | 'not-found',
  ) {
    super(message)
    this.name = 'SignalReadError'
  }
}

export function buildQueueSearch(filters: QueueFilters, now = new Date()): URLSearchParams {
  const search = new URLSearchParams({
    page: String(Math.max(1, filters.page ?? 1)),
    page_size: String(PAGE_SIZE),
  })
  const query = filters.query?.trim()
  const district = filters.district?.trim()
  if (query) search.set('query', query)
  if (district) search.set('district', district)

  const state = UI_TO_API_STATE[filters.state ?? 'todos']
  const priority = UI_TO_API_PRIORITY[filters.priority ?? 'todas']
  if (state) search.set('state', state)
  if (priority) search.set('priority_band', priority)
  if (filters.sourceType === 'midia' || filters.sourceType === 'comunidade') search.set('source_kind', SOURCE_TO_API[filters.sourceType])

  const periodDays = PERIOD_DAYS[filters.period ?? 'todos']
  if (periodDays) search.set('period_start', isoDateDaysBefore(now, periodDays))
  return search
}

export function filtersFromSearchParams(searchParams: Record<string, string | string[] | undefined>): QueueFilters {
  return {
    query: first(searchParams.query),
    state: API_TO_UI_STATE[first(searchParams.state) ?? ''] ?? 'todos',
    priority: API_TO_UI_PRIORITY[first(searchParams.priority_band) ?? ''] ?? 'todas',
    district: first(searchParams.district),
    sourceType: API_TO_SOURCE[first(searchParams.source_kind) ?? ''] ?? 'todas',
    period: periodFromStart(first(searchParams.period_start)),
    page: parsePage(first(searchParams.page)),
  }
}

export async function listSignals(filters: QueueFilters): Promise<SignalQueueView> {
  const response = await requestJson(`/signals?${buildQueueSearch(filters).toString()}`)
  if (!isRecord(response) || !Array.isArray(response.items) || !Number.isInteger(response.page) || !Number.isInteger(response.page_size) || !Number.isInteger(response.total)) {
    throw new SignalReadError('A API retornou uma fila de sinais em formato inválido.', 'invalid-response')
  }
  return {
    items: response.items.map((item) => mapQueueSignal(requireQueueSignal(item))),
    page: Number(response.page),
    pageSize: Number(response.page_size),
    total: Number(response.total),
  }
}

export async function getSignalDetail(signalId: string): Promise<SignalDetailView> {
  const response = await requestJson(`/signals/${encodeURIComponent(signalId)}`)
  if (!isRecord(response)) throw new SignalReadError('A API retornou um detalhe de sinal inválido.', 'invalid-response')
  return mapSignalDetail(response as ApiSignalDetail)
}

export function mapSignalDetail(detail: ApiSignalDetail): SignalDetailView {
  const sources = (detail.sources ?? []).map(mapSource)
  const signal = { ...mapQueueSignal(detail.signal), sourceIds: sources.map((source) => source.id) }
  const relations = detail.relations ?? []
  return {
    signal: {
      ...signal,
      divergences: detail.grouping?.divergence_codes ?? [],
      criteria: mapGroupingCriteria(detail.grouping, relations),
    },
    sources,
    criteria: mapGroupingCriteria(detail.grouping, relations),
    audit: (detail.audit_events ?? []).map(mapAuditEvent),
    workflow: {
      state: API_TO_UI_STATE[detail.signal.workflow.state],
      version: detail.signal.workflow.version,
      updatedAt: detail.signal.workflow.updated_at,
    },
    reviewTargets: [
      {
        type: 'grouping',
        id: detail.signal.id,
        suggestionIdentityKey: detail.grouping.identity_key,
        label: 'Agrupamento sugerido',
      },
      ...(detail.signal.priority
        ? [{
            type: 'priority' as const,
            id: detail.signal.priority.id,
            suggestionIdentityKey: detail.signal.priority.identity_key,
            label: 'Prioridade sugerida',
          }]
        : []),
    ],
  }
}

function mapQueueSignal(item: ApiQueueSignal): Signal {
  const priority = item.priority ? API_TO_UI_PRIORITY[item.priority.band] : null
  return {
    id: item.id,
    code: item.id,
    slug: item.id,
    title: item.title,
    subtitle: item.summary,
    condition: item.conditions[0] ?? 'Não informada',
    symptoms: item.symptoms,
    municipality: item.location.municipality ?? 'Não informado',
    neighborhood: item.location.district ?? 'Não informado',
    periodStart: item.period_start,
    periodEnd: item.period_end,
    magnitude: null,
    priority,
    priorityRationale: item.priority
      ? `Sugestão calculada pela política ${item.priority.policy_version}; score ${item.priority.score} e confiança ${item.priority.confidence}%.`
      : 'Não há sugestão de prioridade disponível para este sinal.',
    state: API_TO_UI_STATE[item.workflow.state],
    createdAt: null,
    updatedAt: item.workflow.updated_at,
    sourceIds: [],
    sourceCounts: {
      midia: item.source_counts.media,
      comunidade: item.source_counts.community,
      total: item.source_counts.total,
    },
    criteria: [],
    divergences: [],
  }
}

function mapSource(source: ApiSource): SourceRecord {
  return {
    id: source.normalized_record_id,
    code: source.normalized_record_id,
    signalId: '',
    type: source.source_kind === 'media' ? 'midia' : 'comunidade',
    subtype: source.source_kind === 'media' ? 'Registro de mídia' : 'Registro comunitário',
    title: source.title ?? 'Título não informado',
    excerpt: source.excerpt,
    origin: source.source_name,
    publishedAt: source.published_at,
    municipality: stringValue(sheetLocation(source.technical_sheet)?.municipality) ?? 'Não informado',
    neighborhood: stringValue(sheetLocation(source.technical_sheet)?.district) ?? 'Não informado',
    isContext: source.role !== 'core',
    sheet: mapTechnicalSheet(source.technical_sheet),
  }
}

function mapTechnicalSheet(sheet: Record<string, unknown> | null): TechnicalSheet | null {
  if (!sheet) return null
  const location = sheetLocation(sheet)
  const temporal = recordAt(sheet, 'temporal')
  const symptoms = stringArray(sheet.symptoms)
  const condition = stringValue(sheet.disease_or_condition) ?? stringValue(sheet.syndrome)
  const period = compact([stringValue(temporal?.start), stringValue(temporal?.end)]).join(' — ') || null
  const magnitude = numberValue(sheet.estimated_cases)
  return {
    condition,
    symptoms,
    location: compact([stringValue(location?.municipality), stringValue(location?.district)]).join(', ') || null,
    period,
    magnitude: magnitude === null ? null : `${magnitude} caso${magnitude === 1 ? '' : 's'}`,
    missingFields: [
      !condition && 'Condição mencionada',
      symptoms.length === 0 && 'Sintomas',
      !location?.municipality && 'Localização',
      !period && 'Período',
      magnitude === null && 'Magnitude',
    ].filter(Boolean) as string[],
    extractionVersion: stringValue(sheet.schema_version) ?? 'Não informada',
    extractedAt: null,
  }
}

function mapGroupingCriteria(
  grouping: ApiSignalDetail['grouping'] | undefined,
  relations: ApiRelation[],
): GroupingCriterion[] {
  const criteria: GroupingCriterion[] = grouping
    ? [{ label: 'Política de agrupamento', detail: `${grouping.policy_version} · estado ${grouping.processing_state}`, met: true }]
    : []
  for (const relation of relations) {
    criteria.push({
      label: `Relação sugerida: ${relation.relation ?? 'não classificada'}`,
      detail: compact([
        relation.justification,
        relation.confidence === null ? null : `confiança ${Math.round(relation.confidence * 100)}%`,
        relation.method,
      ]).join(' · ') || 'Sem justificativa disponível.',
      met: relation.state === 'succeeded',
    })
  }
  return criteria
}

function mapAuditEvent(event: ApiAuditEvent): AuditEvent {
  return {
    id: event.id,
    signalId: event.target_id,
    at: event.occurred_at,
    actor: 'analista',
    actorLabel: event.actor_id,
    title: auditTitle(event.action),
    description: compact([event.reason_code, event.comment]).join(' · ') || `Estado do fluxo: ${event.workflow_state}.`,
  }
}

function auditTitle(action: string): string {
  const titles: Record<string, string> = {
    accept: 'Sugestão aceita',
    correct: 'Sugestão corrigida',
    reject: 'Sugestão rejeitada',
    transition: 'Fluxo atualizado',
  }
  return titles[action] ?? `Ação registrada: ${action}`
}

async function requestJson(path: string): Promise<unknown> {
  let response: Response
  try {
    response = await fetch(`${internalApiBaseUrl()}${path}`, {
      cache: 'no-store',
      headers: { Accept: 'application/json' },
      signal: AbortSignal.timeout(5_000),
    })
  } catch {
    throw new SignalReadError('Não foi possível consultar a API de sinais.', 'unavailable')
  }
  if (response.status === 404) throw new SignalReadError('O sinal não foi encontrado.', 'not-found')
  if (!response.ok) throw new SignalReadError('A API de sinais não está disponível no momento.', 'unavailable')
  try {
    return await response.json()
  } catch {
    throw new SignalReadError('A API retornou uma resposta que não é JSON.', 'invalid-response')
  }
}

function internalApiBaseUrl(rawValue = process.env[INTERNAL_API_URL_ENV]): string {
  const configuredValue = rawValue?.trim() || DEFAULT_INTERNAL_API_URL
  let url: URL
  try {
    url = new URL(configuredValue)
  } catch {
    throw new SignalReadError('A URL interna da API é inválida.', 'unavailable')
  }
  if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password || url.search || url.hash) {
    throw new SignalReadError('A URL interna da API não é segura.', 'unavailable')
  }
  return url.toString().replace(/\/$/, '')
}

function requireQueueSignal(value: unknown): ApiQueueSignal {
  if (!isRecord(value) || typeof value.id !== 'string' || typeof value.title !== 'string' || !isRecord(value.workflow) || !isRecord(value.location)) {
    throw new SignalReadError('A API retornou um sinal de fila inválido.', 'invalid-response')
  }
  return value as ApiQueueSignal
}

const API_TO_UI_STATE: Record<string, WorkflowState> = {
  detected: 'detectado',
  triage: 'triagem',
  verification: 'verificacao',
  risk_assessment: 'avaliacao_risco',
  closed: 'encerrado',
}
const UI_TO_API_STATE: Record<string, string | undefined> = Object.fromEntries(
  Object.entries(API_TO_UI_STATE).map(([api, ui]) => [ui, api]),
) as Record<string, string | undefined>
const API_TO_UI_PRIORITY: Record<string, SuggestedPriority> = { prompt: 'urgente', attention: 'atencao', routine: 'monitorar' }
const UI_TO_API_PRIORITY: Record<string, string | undefined> = Object.fromEntries(
  Object.entries(API_TO_UI_PRIORITY).map(([api, ui]) => [ui, api]),
) as Record<string, string | undefined>
const SOURCE_TO_API: Record<'midia' | 'comunidade', 'media' | 'community'> = { midia: 'media', comunidade: 'community' }
const API_TO_SOURCE: Record<string, 'midia' | 'comunidade'> = { media: 'midia', community: 'comunidade' }
const PERIOD_DAYS: Record<string, number | undefined> = { '24h': 1, '7d': 7, '14d': 14, todos: undefined }

function isoDateDaysBefore(now: Date, days: number): string {
  const date = new Date(now)
  date.setDate(date.getDate() - days)
  return date.toISOString().slice(0, 10)
}

function periodFromStart(value: string | undefined): QueueFilters['period'] {
  if (!value) return 'todos'
  const start = new Date(`${value}T00:00:00.000Z`)
  if (Number.isNaN(start.getTime())) return 'todos'
  const today = new Date()
  today.setUTCHours(0, 0, 0, 0)
  const days = Math.round((today.getTime() - start.getTime()) / 86_400_000)
  if (days === 1) return '24h'
  if (days === 7) return '7d'
  if (days === 14) return '14d'
  return 'todos'
}

function parsePage(value: string | undefined): number {
  const page = Number(value)
  return Number.isInteger(page) && page > 0 ? page : 1
}

function first(value: string | string[] | undefined): string | undefined {
  return Array.isArray(value) ? value[0] : value
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function recordAt(value: Record<string, unknown>, key: string): Record<string, unknown> | null {
  const nested = value[key]
  return isRecord(nested) ? nested : null
}

function stringValue(value: unknown): string | null {
  return typeof value === 'string' && value.trim() ? value : null
}

function stringArray(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string') : []
}

function numberValue(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null
}

function sheetLocation(sheet: Record<string, unknown> | null): Record<string, unknown> | null {
  return sheet ? recordAt(sheet, 'location') : null
}

function compact(values: Array<string | null | undefined>): string[] {
  return values.filter((value): value is string => Boolean(value))
}
