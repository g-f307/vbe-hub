import { afterEach, describe, expect, it, vi } from 'vitest'

import {
  buildIndividualSignalSearch,
  getInvestigation,
  getIndividualSignal,
  listIndividualSignals,
  listRelatedSignals,
  listSignalAuditEvents,
} from './individual-signal-read'

const card = {
  id: '018f6d5d-9c44-7b10-8000-000000000001',
  state: 'detected',
  created_at: '2026-11-08T09:00:00Z',
  source: {
    kind: 'community',
    name: 'Guardiões da Saúde',
    published_at: '2026-11-08T08:00:00Z',
    title: 'Relatos de febre e manchas no bairro',
    excerpt: 'Moradores relatam pessoas com febre e manchas vermelhas.',
  },
  active_investigation_id: null,
}

afterEach(() => vi.unstubAllGlobals())

describe('contrato de sinais individuais', () => {
  it('serializa somente filtros aceitos pelo endpoint versionado', () => {
    expect(Object.fromEntries(buildIndividualSignalSearch({
      state: 'detected',
      sourceKind: 'community',
      cursor: 'cursor-seguro',
      limit: 20,
    }))).toEqual({
      limit: '20',
      state: 'detected',
      source_kind: 'community',
      cursor: 'cursor-seguro',
    })
  })

  it('lê a fila em /v1 como um sinal por fonte', async () => {
    const fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify({
      items: [card],
      next_cursor: 'proxima-pagina',
    }), { status: 200, headers: { 'content-type': 'application/json' } }))
    vi.stubGlobal('fetch', fetch)

    const page = await listIndividualSignals({ state: 'detected', limit: 20 })

    expect(fetch).toHaveBeenCalledWith(
      'http://api:8000/v1/signals?limit=20&state=detected',
      expect.objectContaining({ cache: 'no-store' }),
    )
    expect(page).toEqual({
      items: [expect.objectContaining({
        id: card.id,
        title: card.source.title,
        sourceKind: 'community',
        sourceName: 'Guardiões da Saúde',
      })],
      nextCursor: 'proxima-pagina',
    })
  })

  it('lê detalhe e relacionados persistidos sem disparar provedor externo', async () => {
    const detail = {
      ...card,
      contract_version: 'individual-signal-v1',
      source: {
        ...card.source,
        external_id: 'community-001',
        body: 'Texto integral preservado da fonte.',
        source_url: null,
        language: 'pt-BR',
      },
      provenance: {
        adapter_name: 'synthetic-community',
        adapter_version: '1.0',
        generator_name: 'vbe-hub',
        generator_version: '1.0',
        seed: 307,
        scenario_id: 'scenario-001',
        collected_at: '2026-11-08T09:00:00Z',
      },
      technical_sheet: { symptoms: ['febre', 'manchas'], location: { district: 'Flores' } },
    }
    const related = {
      items: [{
        suggestion_id: '028f6d5d-9c44-7b10-8000-000000000002',
        status: 'ready',
        updated_at: '2026-11-08T09:05:00Z',
        error_code: null,
        relation: 'corroborates',
        confidence: 0.88,
        justification: 'Mesmo local, período e sintomas.',
        candidate: { ...card, id: '038f6d5d-9c44-7b10-8000-000000000003' },
      }],
      next_cursor: null,
    }
    const fetch = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify(detail), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify(related), { status: 200 }))
    vi.stubGlobal('fetch', fetch)

    const [signal, suggestions] = await Promise.all([
      getIndividualSignal(card.id),
      listRelatedSignals(card.id),
    ])

    expect(signal.source.body).toBe('Texto integral preservado da fonte.')
    expect(signal.technicalSheet).toEqual(detail.technical_sheet)
    expect(suggestions.items[0]).toEqual(expect.objectContaining({
      status: 'ready',
      confidence: 0.88,
      candidate: expect.objectContaining({ id: related.items[0].candidate.id }),
    }))
    expect(fetch).toHaveBeenCalledTimes(2)
    expect(fetch.mock.calls.map(([url]) => url)).toEqual([
      `http://api:8000/v1/signals/${card.id}`,
      `http://api:8000/v1/signals/${card.id}/related?limit=25`,
    ])
  })

  it('lê a trilha auditável do workflow individual', async () => {
    const fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify([{
      id: 'audit-1',
      operation_key: 'triage-signal-1',
      subject_type: 'signal',
      subject_id: card.id,
      sequence: 1,
      workflow_version: 1,
      workflow_state: 'triage',
      state_machine_version: 'workflow-v2',
      actor_id: 'analista-demo',
      occurred_at: '2026-11-08T10:00:00Z',
      previous_value: { state: 'detected' },
      new_value: { state: 'triage' },
      reason_code: null,
      comment: 'Revisão inicial.',
    }]), { status: 200 }))
    vi.stubGlobal('fetch', fetch)

    const events = await listSignalAuditEvents(card.id)

    expect(events).toEqual([expect.objectContaining({
      id: 'audit-1',
      state: 'triage',
      actorId: 'analista-demo',
      comment: 'Revisão inicial.',
    })])
    expect(fetch).toHaveBeenCalledWith(
      `http://api:8000/v1/signals/${card.id}/audit-events`,
      expect.objectContaining({ cache: 'no-store' }),
    )
  })

  it('lê a ficha ativa preservando membros e eventos individualizados', async () => {
    const fileId = '048f6d5d-9c44-7b10-8000-000000000004'
    const fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify({
      id: fileId,
      version: 2,
      created_at: '2026-11-08T10:00:00Z',
      updated_at: '2026-11-08T10:05:00Z',
      members: [{
        added_at: '2026-11-08T10:00:00Z',
        added_by: 'analista-demo',
        signal: {
          ...card,
          contract_version: 'individual-signal-v1',
          source: { ...card.source, external_id: null, body: 'Descrição individual.', source_url: null, language: 'pt-BR' },
          provenance: { adapter_name: 'test', adapter_version: '1', generator_name: null, generator_version: null, seed: null, scenario_id: null, collected_at: '2026-11-08T09:00:00Z' },
          technical_sheet: null,
          active_investigation_id: fileId,
        },
      }],
      events: [{ sequence: 1, action: 'add', signal_id: card.id, actor_id: 'analista-demo', occurred_at: '2026-11-08T10:00:00Z', reason_code: null }],
    }), { status: 200 }))
    vi.stubGlobal('fetch', fetch)

    const investigation = await getInvestigation(fileId)

    expect(investigation).toMatchObject({
      id: fileId,
      version: 2,
      members: [{ signal: { id: card.id, source: { body: 'Descrição individual.' } } }],
      events: [{ action: 'add', actorId: 'analista-demo' }],
    })
  })
})
