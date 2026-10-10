export type ApiWorkflowState = 'detected' | 'triage' | 'verification' | 'risk_assessment' | 'closed'
export type ReviewAction = 'accept' | 'correct' | 'reject'
export type ReviewTargetType = 'grouping' | 'priority'

export type TransitionInput = {
  operationKey: string
  expectedVersion: number
  targetState: ApiWorkflowState
  reasonCode?: string
  comment?: string
}

export type ReviewInput = {
  operationKey: string
  expectedVersion: number
  targetType: ReviewTargetType
  targetId: string
  suggestionIdentityKey: string
  action: ReviewAction
  correctedValue?: Record<string, string | number | boolean | null>
  reasonCode?: string
  comment?: string
}

export type WorkflowOutcome = {
  workflow: {
    state: ApiWorkflowState
    version: number
    updated_at: string
  }
  event: {
    id: string
    workflow_state: ApiWorkflowState
    workflow_version: number
    actor_id: string
    occurred_at: string
    action: string
    target_id: string
    reason_code: string | null
    comment: string | null
  }
}

export class WorkflowActionError extends Error {
  constructor(
    message: string,
    readonly kind: 'conflict' | 'validation' | 'not-found' | 'unavailable' | 'invalid-response',
    readonly code?: string,
    readonly currentVersion?: number,
  ) {
    super(message)
    this.name = 'WorkflowActionError'
  }
}

export function createOperationKey(prefix: 'review' | 'transition'): string {
  return `${prefix}-${crypto.randomUUID()}`
}

export function transitionPayload(input: TransitionInput) {
  return compact({
    operation_key: input.operationKey,
    expected_version: input.expectedVersion,
    target_state: input.targetState,
    reason_code: input.reasonCode,
    comment: input.comment,
  })
}

export function reviewPayload(input: ReviewInput) {
  return compact({
    operation_key: input.operationKey,
    expected_version: input.expectedVersion,
    target_type: input.targetType,
    target_id: input.targetId,
    suggestion_identity_key: input.suggestionIdentityKey,
    action: input.action,
    corrected_value: input.correctedValue,
    reason_code: input.reasonCode,
    comment: input.comment,
  })
}

export async function submitTransition(signalId: string, input: TransitionInput): Promise<WorkflowOutcome> {
  return postWorkflow(`/api/signals/${encodeURIComponent(signalId)}/workflow/transitions`, transitionPayload(input))
}

export async function submitReview(signalId: string, input: ReviewInput): Promise<WorkflowOutcome> {
  return postWorkflow(`/api/signals/${encodeURIComponent(signalId)}/reviews`, reviewPayload(input))
}

export function classifyWorkflowError(status: number, detail: unknown): WorkflowActionError {
  const body = isRecord(detail) ? detail : {}
  const code = typeof body.code === 'string' ? body.code : undefined
  const currentVersion = typeof body.current_version === 'number' ? body.current_version : undefined
  if (status === 409 && code === 'workflow_version_conflict') {
    return new WorkflowActionError('Este sinal foi alterado por outra revisão. Recarregue antes de continuar.', 'conflict', code, currentVersion)
  }
  if (status === 404) return new WorkflowActionError('O sinal não está mais disponível para revisão.', 'not-found', code)
  if (status === 422 || status === 409) return new WorkflowActionError(validationMessage(code), 'validation', code)
  return new WorkflowActionError('Não foi possível registrar a ação agora. Tente novamente.', 'unavailable', code)
}

async function postWorkflow(path: string, payload: object): Promise<WorkflowOutcome> {
  let response: Response
  try {
    response = await fetch(path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify(payload),
    })
  } catch {
    throw new WorkflowActionError('Não foi possível alcançar o serviço de revisão.', 'unavailable')
  }
  const body = await jsonOrNull(response)
  if (!response.ok) throw classifyWorkflowError(response.status, isRecord(body) ? body.detail : body)
  if (!isWorkflowOutcome(body)) throw new WorkflowActionError('A API retornou uma confirmação inválida.', 'invalid-response')
  return body
}

function validationMessage(code?: string): string {
  const messages: Record<string, string> = {
    closure_reason_required: 'Selecione o motivo estruturado para encerrar o sinal.',
    corrected_value_required: 'Informe o campo e o valor propostos para a correção.',
    reason_code_required: 'Informe o motivo estruturado para esta decisão.',
    review_target_not_found: 'A sugestão não está mais disponível para revisão.',
    invalid_workflow_transition: 'A transição solicitada não é permitida no estado atual.',
  }
  return messages[code ?? ''] ?? 'A ação não atende às regras de revisão. Confira os campos e tente novamente.'
}

function compact<T extends Record<string, unknown>>(value: T): T {
  return Object.fromEntries(Object.entries(value).filter(([, item]) => item !== undefined && item !== '')) as T
}

async function jsonOrNull(response: Response): Promise<unknown> {
  try {
    return await response.json()
  } catch {
    return null
  }
}

function isWorkflowOutcome(value: unknown): value is WorkflowOutcome {
  return isRecord(value) && isRecord(value.workflow) && isRecord(value.event)
    && typeof value.workflow.state === 'string' && typeof value.workflow.version === 'number'
    && typeof value.event.id === 'string'
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}
