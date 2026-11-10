import type { RelatedSignal } from './individual-signal-read'

export type InvestigationSignal = {
  id: string
  title: string
  body: string
  sourceKind: 'media' | 'community'
  sourceName: string
  publishedAt: string
}

export type InvestigationMember = {
  addedAt: string
  addedBy: string
  signal: InvestigationSignal
}

export type InvestigationEvent = {
  sequence: number
  action: 'add' | 'remove' | 'reject'
  signalId: string
  actorId: string
  occurredAt: string
  reasonCode: string | null
}

export type InvestigationDetail = {
  id: string
  headSignalId: string
  version: number
  createdAt: string
  updatedAt: string
  members: InvestigationMember[]
  events: InvestigationEvent[]
  technicalSheet: Record<string, unknown>
  technicalSheetProvenance: Record<string, string[]>
  technicalSheetConflicts: Array<Record<string, unknown>>
}

export class InvestigationActionError extends Error {
  constructor(
    message: string,
    readonly kind: 'conflict' | 'validation' | 'not-found' | 'unavailable' | 'invalid-response',
    readonly code?: string,
    readonly currentVersion?: number,
  ) {
    super(message)
    this.name = 'InvestigationActionError'
  }
}

export function selectableRelatedSignals(items: RelatedSignal[]): RelatedSignal[] {
  return items.filter((item) => item.status === 'ready' && item.candidate.activeInvestigationId === null)
}

export function hideInvestigationMembers(items: RelatedSignal[], memberIds: string[]): RelatedSignal[] {
  const members = new Set(memberIds)
  return items.filter((item) => !members.has(item.candidate.id))
}

export function buildCompositionPayload(input: {
  primarySignalId: string
  selectedSignalIds: string[]
  operationKey: string
}) {
  return {
    primary_signal_id: input.primarySignalId,
    selected_signal_ids: [...new Set(input.selectedSignalIds)].filter((id) => id !== input.primarySignalId),
    operation_key: input.operationKey,
  }
}

export function createInvestigationOperationKey(prefix: 'compose' | 'remove'): string {
  return `${prefix}-${crypto.randomUUID()}`
}

export async function composeInvestigation(input: {
  primarySignalId: string
  selectedSignalIds: string[]
  operationKey: string
}): Promise<InvestigationDetail> {
  return postInvestigation('/api/investigations/compositions', buildCompositionPayload(input))
}

export async function removeInvestigationMember(input: {
  investigationId: string
  signalId: string
  expectedVersion: number
  operationKey: string
  reasonCode: string
}): Promise<InvestigationDetail> {
  return postInvestigation(
    `/api/investigations/${encodeURIComponent(input.investigationId)}/members/${encodeURIComponent(input.signalId)}/removals`,
    {
      operation_key: input.operationKey,
      expected_version: input.expectedVersion,
      reason_code: input.reasonCode,
    },
  )
}

export function classifyInvestigationError(status: number, detail: unknown): InvestigationActionError {
  const body = isRecord(detail) ? detail : {}
  const code = typeof body.code === 'string' ? body.code : undefined
  const currentVersion = typeof body.current_version === 'number' ? body.current_version : undefined
  if (status === 409 && code === 'investigation_version_conflict') {
    return new InvestigationActionError(
      'A ficha foi alterada por outra ação. Recarregue antes de continuar.',
      'conflict',
      code,
      currentVersion,
    )
  }
  if (status === 404) return new InvestigationActionError('A ficha ou o sinal não está mais disponível.', 'not-found', code)
  if (status === 409 || status === 422) {
    return new InvestigationActionError(validationMessage(code), 'validation', code, currentVersion)
  }
  return new InvestigationActionError('Não foi possível registrar a decisão agora. Tente novamente.', 'unavailable', code)
}

async function postInvestigation(path: string, payload: object): Promise<InvestigationDetail> {
  let response: Response
  try {
    response = await fetch(path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify(payload),
    })
  } catch {
    throw new InvestigationActionError('Não foi possível alcançar o serviço de investigação.', 'unavailable')
  }
  const body = await jsonOrNull(response)
  if (!response.ok) throw classifyInvestigationError(response.status, isRecord(body) ? body.detail : body)
  return mapInvestigation(body)
}

export function mapInvestigation(value: unknown): InvestigationDetail {
  if (!isRecord(value) || !Array.isArray(value.members) || !Array.isArray(value.events)) {
    throw new InvestigationActionError('A API retornou uma ficha inválida.', 'invalid-response')
  }
  return {
    id: requiredString(value.id),
    headSignalId: requiredString(value.head_signal_id),
    version: requiredNumber(value.version),
    createdAt: requiredString(value.created_at),
    updatedAt: requiredString(value.updated_at),
    technicalSheet: isRecord(value.technical_sheet) ? value.technical_sheet : {},
    technicalSheetProvenance: stringArrayRecord(value.technical_sheet_provenance),
    technicalSheetConflicts: Array.isArray(value.technical_sheet_conflicts)
      ? value.technical_sheet_conflicts.filter(isRecord)
      : [],
    members: value.members.map((member) => {
      if (!isRecord(member) || !isRecord(member.signal) || !isRecord(member.signal.source)) invalid()
      return {
        addedAt: requiredString(member.added_at),
        addedBy: requiredString(member.added_by),
        signal: {
          id: requiredString(member.signal.id),
          title: typeof member.signal.source.title === 'string' ? member.signal.source.title : 'Sinal sem título informado',
          body: requiredString(member.signal.source.body),
          sourceKind: sourceKind(member.signal.source.kind),
          sourceName: requiredString(member.signal.source.name),
          publishedAt: requiredString(member.signal.source.published_at),
        },
      }
    }),
    events: value.events.map((event) => {
      if (!isRecord(event)) invalid()
      const action = requiredString(event.action)
      if (!['add', 'remove', 'reject'].includes(action)) invalid()
      return {
        sequence: requiredNumber(event.sequence),
        action: action as InvestigationEvent['action'],
        signalId: requiredString(event.signal_id),
        actorId: requiredString(event.actor_id),
        occurredAt: requiredString(event.occurred_at),
        reasonCode: typeof event.reason_code === 'string' ? event.reason_code : null,
      }
    }),
  }
}

function validationMessage(code?: string): string {
  const messages: Record<string, string> = {
    signal_already_assigned: 'Um dos sinais já pertence a outra ficha de investigação.',
    signal_not_in_triage: 'Um dos sinais ainda não está disponível para composição.',
    investigation_requires_member: 'Uma ficha não pode ficar sem sinais.',
    investigation_head_cannot_be_removed: 'O sinal-cabeça não pode ser removido da própria investigação.',
    operation_key_conflict: 'Esta operação já foi utilizada com outro conteúdo.',
    invalid_composition: 'Selecione ao menos um sinal relacionado válido.',
  }
  return messages[code ?? ''] ?? 'A decisão não atende às regras da investigação. Recarregue e confira os sinais.'
}

function stringArrayRecord(value: unknown): Record<string, string[]> {
  if (!isRecord(value)) return {}
  return Object.fromEntries(
    Object.entries(value).filter((entry): entry is [string, string[]] =>
      Array.isArray(entry[1]) && entry[1].every((item) => typeof item === 'string'),
    ),
  )
}

async function jsonOrNull(response: Response): Promise<unknown> {
  try {
    return await response.json()
  } catch {
    return null
  }
}

function invalid(): never {
  throw new InvestigationActionError('A API retornou uma ficha inválida.', 'invalid-response')
}

function requiredString(value: unknown): string {
  if (typeof value !== 'string' || value.length === 0) invalid()
  return value
}

function requiredNumber(value: unknown): number {
  if (typeof value !== 'number' || !Number.isInteger(value)) invalid()
  return value
}

function sourceKind(value: unknown): 'media' | 'community' {
  if (value !== 'media' && value !== 'community') invalid()
  return value
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}
