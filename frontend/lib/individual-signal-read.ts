const DEFAULT_INTERNAL_API_URL = 'http://api:8000'

export type IndividualSignalState = 'detected' | 'triage' | 'verification' | 'risk_assessment' | 'closed'
export type IndividualSourceKind = 'media' | 'community'
export type RelatedStatus = 'pending' | 'ready' | 'failed'

export type IndividualSignalCard = {
  id: string
  state: IndividualSignalState
  createdAt: string
  title: string
  excerpt: string
  sourceKind: IndividualSourceKind
  sourceName: string
  publishedAt: string
  activeInvestigationId: string | null
}

export type SignalProvenance = {
  adapterName: string
  adapterVersion: string
  generatorName: string | null
  generatorVersion: string | null
  seed: number | null
  scenarioId: string | null
  collectedAt: string
}

export type IndividualSignalDetail = IndividualSignalCard & {
  contractVersion: string
  source: {
    externalId: string | null
    body: string
    url: string | null
    language: string
  }
  provenance: SignalProvenance
  technicalSheet: Record<string, unknown> | null
}

export type RelatedSignal = {
  suggestionId: string
  status: RelatedStatus
  updatedAt: string
  errorCode: string | null
  relation: string | null
  confidence: number | null
  justification: string | null
  candidate: IndividualSignalCard
}

export type IndividualSignalPage = { items: IndividualSignalCard[]; nextCursor: string | null }
export type RelatedSignalPage = { items: RelatedSignal[]; nextCursor: string | null }
export type SignalAuditEvent = {
  id: string
  sequence: number
  version: number
  state: IndividualSignalState
  actorId: string
  occurredAt: string
  previousValue: Record<string, string>
  newValue: Record<string, string>
  reasonCode: string | null
  comment: string | null
}

export type IndividualSignalFilters = {
  state?: IndividualSignalState
  sourceKind?: IndividualSourceKind
  cursor?: string
  limit?: number
}

export class IndividualSignalReadError extends Error {
  constructor(
    message: string,
    readonly kind: 'unavailable' | 'invalid-response' | 'not-found',
  ) {
    super(message)
    this.name = 'IndividualSignalReadError'
  }
}

export function buildIndividualSignalSearch(filters: IndividualSignalFilters): URLSearchParams {
  const search = new URLSearchParams({ limit: String(Math.min(100, Math.max(1, Math.trunc(filters.limit ?? 25)))) })
  if (filters.state) search.set('state', filters.state)
  if (filters.sourceKind) search.set('source_kind', filters.sourceKind)
  if (filters.cursor?.trim()) search.set('cursor', filters.cursor.trim())
  return search
}

export async function listIndividualSignals(filters: IndividualSignalFilters = {}): Promise<IndividualSignalPage> {
  const payload = await request(`/v1/signals?${buildIndividualSignalSearch(filters)}`)
  if (!isRecord(payload) || !Array.isArray(payload.items)) invalid('A fila de sinais individuais é inválida.')
  return {
    items: payload.items.map(mapCard),
    nextCursor: nullableString(payload.next_cursor),
  }
}

export async function getIndividualSignal(signalId: string): Promise<IndividualSignalDetail> {
  const payload = await request(`/v1/signals/${encodeURIComponent(signalId)}`)
  if (!isRecord(payload) || !isRecord(payload.source) || !isRecord(payload.provenance)) invalid('O detalhe do sinal individual é inválido.')
  const card = mapCard(payload)
  return {
    ...card,
    contractVersion: requiredString(payload.contract_version),
    source: {
      externalId: nullableString(payload.source.external_id),
      body: requiredString(payload.source.body),
      url: nullableString(payload.source.source_url),
      language: requiredString(payload.source.language),
    },
    provenance: {
      adapterName: requiredString(payload.provenance.adapter_name),
      adapterVersion: requiredString(payload.provenance.adapter_version),
      generatorName: nullableString(payload.provenance.generator_name),
      generatorVersion: nullableString(payload.provenance.generator_version),
      seed: nullableNumber(payload.provenance.seed),
      scenarioId: nullableString(payload.provenance.scenario_id),
      collectedAt: requiredString(payload.provenance.collected_at),
    },
    technicalSheet: isRecord(payload.technical_sheet) ? payload.technical_sheet : null,
  }
}

export async function listRelatedSignals(signalId: string, cursor?: string): Promise<RelatedSignalPage> {
  const search = new URLSearchParams({ limit: '25' })
  if (cursor) search.set('cursor', cursor)
  const payload = await request(`/v1/signals/${encodeURIComponent(signalId)}/related?${search}`)
  if (!isRecord(payload) || !Array.isArray(payload.items)) invalid('As sugestões relacionadas são inválidas.')
  return {
    items: payload.items.map((item) => {
      if (!isRecord(item) || !isRecord(item.candidate)) invalid('Uma sugestão relacionada é inválida.')
      const status = requiredString(item.status)
      if (!isRelatedStatus(status)) invalid('O estado da sugestão relacionada é inválido.')
      return {
        suggestionId: requiredString(item.suggestion_id),
        status,
        updatedAt: requiredString(item.updated_at),
        errorCode: nullableString(item.error_code),
        relation: nullableString(item.relation),
        confidence: nullableNumber(item.confidence),
        justification: nullableString(item.justification),
        candidate: mapCard(item.candidate),
      }
    }),
    nextCursor: nullableString(payload.next_cursor),
  }
}

export async function listSignalAuditEvents(signalId: string): Promise<SignalAuditEvent[]> {
  const payload = await request(`/v1/signals/${encodeURIComponent(signalId)}/audit-events`)
  if (!Array.isArray(payload)) invalid('A trilha de auditoria do sinal é inválida.')
  return payload.map((item) => {
    if (!isRecord(item)) invalid('Um evento da trilha de auditoria é inválido.')
    const state = requiredString(item.workflow_state)
    if (!isSignalState(state)) invalid('O estado de um evento da trilha é inválido.')
    return {
      id: requiredString(item.id),
      sequence: requiredInteger(item.sequence),
      version: requiredInteger(item.workflow_version),
      state,
      actorId: requiredString(item.actor_id),
      occurredAt: requiredString(item.occurred_at),
      previousValue: stringRecord(item.previous_value),
      newValue: stringRecord(item.new_value),
      reasonCode: nullableString(item.reason_code),
      comment: nullableString(item.comment),
    }
  })
}

function mapCard(value: unknown): IndividualSignalCard {
  if (!isRecord(value) || !isRecord(value.source)) invalid('Um card de sinal individual é inválido.')
  const state = requiredString(value.state)
  const sourceKind = requiredString(value.source.kind)
  if (!isSignalState(state) || !isSourceKind(sourceKind)) invalid('O card possui estado ou fonte inválidos.')
  const title = nullableString(value.source.title)
  return {
    id: requiredString(value.id),
    state,
    createdAt: requiredString(value.created_at),
    title: title ?? 'Sinal sem título informado',
    excerpt: requiredString(value.source.excerpt),
    sourceKind,
    sourceName: requiredString(value.source.name),
    publishedAt: requiredString(value.source.published_at),
    activeInvestigationId: nullableString(value.active_investigation_id),
  }
}

async function request(path: string): Promise<unknown> {
  const baseUrl = (process.env.VBE_API_INTERNAL_URL || DEFAULT_INTERNAL_API_URL).replace(/\/$/, '')
  let response: Response
  try {
    response = await fetch(`${baseUrl}${path}`, {
      cache: 'no-store',
      signal: AbortSignal.timeout(8_000),
      headers: { accept: 'application/json' },
    })
  } catch {
    throw new IndividualSignalReadError('A API de sinais individuais está indisponível.', 'unavailable')
  }
  if (response.status === 404) throw new IndividualSignalReadError('Sinal individual não encontrado.', 'not-found')
  if (!response.ok) throw new IndividualSignalReadError('A API de sinais individuais não respondeu corretamente.', 'unavailable')
  try {
    return await response.json()
  } catch {
    throw new IndividualSignalReadError('A API retornou JSON inválido.', 'invalid-response')
  }
}

function invalid(message: string): never {
  throw new IndividualSignalReadError(message, 'invalid-response')
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function requiredString(value: unknown): string {
  if (typeof value !== 'string' || value.length === 0) invalid('Um campo obrigatório está ausente.')
  return value
}

function nullableString(value: unknown): string | null {
  if (value === null || value === undefined) return null
  if (typeof value !== 'string') invalid('Um campo textual é inválido.')
  return value
}

function nullableNumber(value: unknown): number | null {
  if (value === null || value === undefined) return null
  if (typeof value !== 'number' || !Number.isFinite(value)) invalid('Um campo numérico é inválido.')
  return value
}

function requiredInteger(value: unknown): number {
  if (typeof value !== 'number' || !Number.isInteger(value)) invalid('Um campo inteiro é inválido.')
  return value
}

function stringRecord(value: unknown): Record<string, string> {
  if (!isRecord(value) || Object.values(value).some((item) => typeof item !== 'string')) invalid('Um campo de auditoria é inválido.')
  return value as Record<string, string>
}

function isSignalState(value: string): value is IndividualSignalState {
  return ['detected', 'triage', 'verification', 'risk_assessment', 'closed'].includes(value)
}

function isSourceKind(value: string): value is IndividualSourceKind {
  return value === 'media' || value === 'community'
}

function isRelatedStatus(value: string): value is RelatedStatus {
  return value === 'pending' || value === 'ready' || value === 'failed'
}
