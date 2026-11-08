const DEFAULT_INTERNAL_API_URL = 'http://api:8000'
const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
const OPERATION_PATTERN = /^[A-Za-z0-9._@:-]{1,90}$/

type Fetcher = typeof fetch

export async function proxyComposeInvestigation(request: Request, fetcher: Fetcher = fetch): Promise<Response> {
  const input = await requestRecord(request)
  if (!input) return problem(422, 'invalid_request_body')
  const primaryId = stringField(input.primary_signal_id)
  const operationKey = stringField(input.operation_key)
  const selected = Array.isArray(input.selected_signal_ids)
    ? [...new Set(input.selected_signal_ids.filter((item): item is string => typeof item === 'string'))]
    : null
  if (!primaryId || !UUID_PATTERN.test(primaryId) || !operationKey || !OPERATION_PATTERN.test(operationKey) || !selected) {
    return problem(422, 'invalid_composition')
  }
  if (selected.length > 20 || selected.some((id) => !UUID_PATTERN.test(id) || id === primaryId)) {
    return problem(422, 'invalid_composition')
  }

  const primary = await upstreamJson(`/v1/signals/${primaryId}`, undefined, fetcher)
  if (primary.response) return primary.response
  const activeFileId = isRecord(primary.data) && typeof primary.data.active_investigation_id === 'string'
    ? primary.data.active_investigation_id
    : null

  if (activeFileId === null) {
    const primaryTriage = await ensureTriage(primaryId, `${operationKey}:triage:0`, fetcher)
    if (primaryTriage instanceof Response) return primaryTriage
  }
  for (const [index, signalId] of selected.entries()) {
    const triage = await ensureTriage(signalId, `${operationKey}:triage:${index + 1}`, fetcher)
    if (triage instanceof Response) return triage
  }

  let investigation = activeFileId
    ? await upstreamJson(`/v1/investigations/${activeFileId}`, undefined, fetcher)
    : await upstreamJson('/v1/investigations', {
        method: 'POST',
        body: { signal_id: primaryId, operation_key: `${operationKey}:create` },
      }, fetcher)
  if (investigation.response) return investigation.response
  if (!isInvestigation(investigation.data)) return problem(502, 'investigation_service_invalid_response')

  for (const [index, signalId] of selected.entries()) {
    const signal = await upstreamJson(`/v1/signals/${signalId}`, undefined, fetcher)
    if (signal.response) return signal.response
    const assignedTo = isRecord(signal.data) && typeof signal.data.active_investigation_id === 'string'
      ? signal.data.active_investigation_id
      : null
    if (assignedTo === investigation.data.id) continue
    if (assignedTo !== null) return problem(409, 'signal_already_assigned')
    investigation = await upstreamJson(
      `/v1/investigations/${investigation.data.id}/members/${signalId}`,
      {
        method: 'POST',
        body: { operation_key: `${operationKey}:add:${index}`, expected_version: investigation.data.version },
      },
      fetcher,
    )
    if (investigation.response) return investigation.response
    if (!isInvestigation(investigation.data)) return problem(502, 'investigation_service_invalid_response')
  }
  const workflow = await upstreamJson(`/v1/investigations/${investigation.data.id}/workflow`, undefined, fetcher)
  const needsInitialWorkflow = workflow.response?.status === 404
    && isRecord(workflow.data)
    && isRecord(workflow.data.detail)
    && workflow.data.detail.code === 'investigation_not_found'
  if (workflow.response && !needsInitialWorkflow) return workflow.response
  if (needsInitialWorkflow) {
    const verification = await upstreamJson(
      `/v1/investigations/${investigation.data.id}/workflow/transitions`,
      {
        method: 'POST',
        body: {
          operation_key: `${operationKey}:verify`,
          expected_version: 0,
          target_state: 'verification',
          comment: 'Composição da ficha confirmada pelo analista.',
        },
      },
      fetcher,
    )
    if (verification.response) return verification.response
  }
  return jsonResponse(investigation.data)
}

export async function proxyRemoveInvestigationMember(
  request: Request,
  fileId: string,
  signalId: string,
  fetcher: Fetcher = fetch,
): Promise<Response> {
  if (!UUID_PATTERN.test(fileId) || !UUID_PATTERN.test(signalId)) return problem(404, 'investigation_not_found')
  const input = await requestRecord(request)
  if (!input) return problem(422, 'invalid_request_body')
  const payload = {
    operation_key: input.operation_key,
    expected_version: input.expected_version,
    reason_code: input.reason_code,
  }
  const result = await upstreamJson(
    `/v1/investigations/${fileId}/members/${signalId}/removals`,
    { method: 'POST', body: payload },
    fetcher,
  )
  return result.response ?? jsonResponse(result.data)
}

async function ensureTriage(signalId: string, operationKey: string, fetcher: Fetcher): Promise<true | Response> {
  const workflow = await upstreamJson(`/v1/signals/${signalId}/workflow`, undefined, fetcher)
  if (workflow.response) return workflow.response
  if (!isRecord(workflow.data) || typeof workflow.data.state !== 'string' || typeof workflow.data.version !== 'number') {
    return problem(502, 'workflow_service_invalid_response')
  }
  if (workflow.data.state === 'triage') return true
  if (workflow.data.state !== 'detected') return problem(409, 'signal_not_in_triage')
  const transitioned = await upstreamJson(
    `/v1/signals/${signalId}/workflow/transitions`,
    {
      method: 'POST',
      body: {
        operation_key: operationKey,
        expected_version: workflow.data.version,
        target_state: 'triage',
        comment: 'Triagem iniciada para composição humana de ficha.',
      },
    },
    fetcher,
  )
  return transitioned.response ?? true
}

async function upstreamJson(
  path: string,
  options: { method: 'POST'; body: Record<string, unknown> } | undefined,
  fetcher: Fetcher,
): Promise<{ data: unknown; response?: Response }> {
  let upstream: Response
  try {
    upstream = await fetcher(`${internalApiBaseUrl()}${path}`, {
      method: options?.method ?? 'GET',
      headers: { Accept: 'application/json', ...(options ? { 'Content-Type': 'application/json' } : {}) },
      body: options ? JSON.stringify(options.body) : undefined,
      cache: 'no-store',
      redirect: 'error',
      signal: AbortSignal.timeout(8_000),
    })
  } catch {
    return { data: null, response: problem(503, 'investigation_service_unavailable') }
  }
  const data = await responseJson(upstream)
  if (data === null) return { data: null, response: problem(502, 'investigation_service_invalid_response') }
  if (!upstream.ok) return { data, response: jsonResponse(data, upstream.status) }
  return { data }
}

function internalApiBaseUrl(): string {
  const raw = process.env.VBE_API_INTERNAL_URL?.trim() || DEFAULT_INTERNAL_API_URL
  const url = new URL(raw)
  if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password || url.search || url.hash) {
    throw new Error('Unsafe internal API URL')
  }
  return url.toString().replace(/\/$/, '')
}

async function requestRecord(request: Request): Promise<Record<string, unknown> | null> {
  try {
    const value: unknown = await request.json()
    return isRecord(value) ? value : null
  } catch {
    return null
  }
}

async function responseJson(response: Response): Promise<unknown | null> {
  try {
    return await response.json()
  } catch {
    return null
  }
}

function isInvestigation(value: unknown): value is { id: string; version: number } & Record<string, unknown> {
  return isRecord(value) && typeof value.id === 'string' && UUID_PATTERN.test(value.id)
    && typeof value.version === 'number' && Number.isInteger(value.version)
}

function stringField(value: unknown): string | null {
  return typeof value === 'string' ? value : null
}

function jsonResponse(value: unknown, status = 200): Response {
  return Response.json(value, { status, headers: { 'Cache-Control': 'no-store' } })
}

function problem(status: number, code: string): Response {
  return jsonResponse({ detail: { code } }, status)
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}
