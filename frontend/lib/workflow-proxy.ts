import 'server-only'

import { NextResponse } from 'next/server'

const INTERNAL_API_URL_ENV = 'VBE_API_INTERNAL_URL'
const DEFAULT_INTERNAL_API_URL = 'http://api:8000'
const SIGNAL_ID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i

const TRANSITION_FIELDS = ['operation_key', 'expected_version', 'target_state', 'reason_code', 'comment'] as const
const REVIEW_FIELDS = [
  'operation_key',
  'expected_version',
  'target_type',
  'target_id',
  'suggestion_identity_key',
  'action',
  'corrected_value',
  'reason_code',
  'comment',
] as const

type ProxyOperation = 'transition' | 'review'

export async function proxyWorkflowPost(request: Request, signalId: string, operation: ProxyOperation): Promise<NextResponse> {
  if (!SIGNAL_ID_PATTERN.test(signalId)) return problem(404, 'workflow_signal_not_found')

  const input = await requestJson(request)
  if (!input) return problem(422, 'invalid_request_body')

  const payload = pickFields(input, operation === 'transition' ? TRANSITION_FIELDS : REVIEW_FIELDS)
  let upstream: Response
  try {
    upstream = await fetch(`${internalApiBaseUrl()}/signals/${signalId}${operation === 'transition' ? '/workflow/transitions' : '/reviews'}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify(payload),
      cache: 'no-store',
      redirect: 'error',
      signal: AbortSignal.timeout(5_000),
    })
  } catch {
    return problem(503, 'workflow_service_unavailable')
  }

  const data = await responseJson(upstream)
  if (data === null) return problem(502, 'workflow_service_invalid_response')
  return NextResponse.json(data, { status: upstream.status, headers: { 'Cache-Control': 'no-store' } })
}

function internalApiBaseUrl(rawValue = process.env[INTERNAL_API_URL_ENV]): string {
  const configuredValue = rawValue?.trim() || DEFAULT_INTERNAL_API_URL
  let url: URL
  try {
    url = new URL(configuredValue)
  } catch {
    throw new Error('Invalid internal API URL')
  }
  if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password || url.search || url.hash) {
    throw new Error('Unsafe internal API URL')
  }
  return url.toString().replace(/\/$/, '')
}

async function requestJson(request: Request): Promise<Record<string, unknown> | null> {
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

function pickFields<T extends readonly string[]>(input: Record<string, unknown>, fields: T): Partial<Record<T[number], unknown>> {
  const result: Partial<Record<T[number], unknown>> = {}
  for (const field of fields) {
    if (Object.hasOwn(input, field)) result[field as T[number]] = input[field]
  }
  return result
}

function problem(status: number, code: string): NextResponse {
  return NextResponse.json({ detail: { code } }, { status, headers: { 'Cache-Control': 'no-store' } })
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}
