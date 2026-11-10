import { describe, expect, it, vi } from 'vitest'

import { proxyComposeInvestigation, proxyRemoveInvestigationMember } from './investigation-proxy'

const primary = '018f6d5d-9c44-7b10-8000-000000000001'
const candidate = '018f6d5d-9c44-7b10-8000-000000000002'
const fileId = '018f6d5d-9c44-7b10-8000-000000000010'

describe('investigation BFF', () => {
  it('só move e associa os IDs confirmados, reutilizando a versão retornada pela API', async () => {
    const calls: Array<{ url: string; body?: Record<string, unknown> }> = []
    const upstream = vi.fn(async (input: string | URL | Request, init?: RequestInit) => {
      const url = String(input)
      const body = typeof init?.body === 'string' ? JSON.parse(init.body) : undefined
      calls.push({ url, body })
      if (url.endsWith(`/signals/${primary}/workflow`)) return json({ state: 'detected', version: 0 })
      if (url.endsWith(`/signals/${candidate}/workflow`)) return json({ state: 'triage', version: 1 })
      if (url.endsWith(`/signals/${primary}/workflow/transitions`)) return json({ workflow: { state: 'triage', version: 1 }, event: {} })
      if (url.endsWith(`/signals/${primary}`)) return json({ active_investigation_id: null })
      if (url.endsWith(`/signals/${candidate}`)) return json({ active_investigation_id: null })
      if (url.endsWith('/investigations')) return json(investigation(1), 201)
      if (url.endsWith(`/investigations/${fileId}/members/${candidate}`)) return json(investigation(2))
      if (url.endsWith(`/investigations/${fileId}/workflow`)) return json({ detail: { code: 'investigation_not_found' } }, 404)
      if (url.endsWith(`/investigations/${fileId}/workflow/transitions`)) return json({ workflow: { state: 'verification', version: 1 }, event: {} })
      return json({ detail: { code: 'unexpected_test_request' } }, 500)
    })
    const request = new Request('http://frontend/api/investigations/compositions', {
      method: 'POST',
      body: JSON.stringify({
        primary_signal_id: primary,
        selected_signal_ids: [candidate],
        operation_key: 'compose-test-001',
      }),
    })

    const response = await proxyComposeInvestigation(request, upstream as typeof fetch)

    expect(response.status).toBe(200)
    expect(await response.json()).toMatchObject({ id: fileId, version: 2 })
    expect(calls.map((call) => call.body).filter(Boolean)).toEqual([
      { operation_key: 'compose-test-001:triage:0', expected_version: 0, target_state: 'triage', comment: 'Triagem iniciada para composição humana de ficha.' },
      { signal_id: primary, operation_key: 'compose-test-001:create' },
      { operation_key: 'compose-test-001:add:0', expected_version: 1 },
      { operation_key: 'compose-test-001:verify', expected_version: 0, target_state: 'verification', comment: 'Composição da ficha confirmada pelo analista.' },
    ])
  })

  it('encaminha remoção com versão e motivo, sem aceitar campos extras', async () => {
    let forwarded: Record<string, unknown> | undefined
    const upstream = vi.fn(async (_input: string | URL | Request, init?: RequestInit) => {
      forwarded = JSON.parse(String(init?.body))
      return json(investigation(3))
    })
    const request = new Request('http://frontend/api/remove', {
      method: 'POST',
      body: JSON.stringify({ operation_key: 'remove-test', expected_version: 2, reason_code: 'analyst-correction', actor_id: 'forged' }),
    })

    const response = await proxyRemoveInvestigationMember(request, fileId, candidate, upstream as typeof fetch)

    expect(response.status).toBe(200)
    expect(forwarded).toEqual({ operation_key: 'remove-test', expected_version: 2, reason_code: 'analyst-correction' })
  })
})

function investigation(version: number) {
  return {
    id: fileId,
    head_signal_id: primary,
    version,
    created_at: '2026-11-08T10:00:00Z',
    updated_at: '2026-11-08T10:00:00Z',
    members: [],
    events: [],
    technical_sheet: {},
    technical_sheet_provenance: {},
    technical_sheet_conflicts: [],
  }
}

function json(value: unknown, status = 200): Response {
  return new Response(JSON.stringify(value), { status, headers: { 'Content-Type': 'application/json' } })
}
