import { describe, expect, it } from 'vitest'

import { buildQueueSearch, filtersFromSearchParams, mapSignalDetail } from './signal-read'

const signal = {
  id: '6b2c3d4e-8f90-4ba1-9c2d-3e4f5a6b0040',
  title: 'Menções compatíveis em Flores',
  summary: 'Dois registros sintéticos mencionam febre e tosse.',
  conditions: ['Síndrome respiratória'],
  symptoms: ['Febre', 'Tosse'],
  period_start: '2026-10-06',
  period_end: '2026-10-07',
  location: { country: 'Brasil', state: 'Amazonas', municipality: 'Manaus', district: 'Flores', precision: 'district' },
  source_counts: { media: 1, community: 1, total: 2 },
  priority: { id: '8b2c3d4e-8f90-4ba1-9c2d-3e4f5a6b0041', band: 'attention' as const, score: 63, confidence: 78, policy_version: 'priority-v1', identity_key: 'priority-key' },
  workflow: { state: 'triage' as const, version: 2, updated_at: '2026-10-07T12:00:00Z' },
}

describe('buildQueueSearch', () => {
  it('serializa a consulta compartilhável no contrato canônico', () => {
    const search = buildQueueSearch({
      query: 'febre',
      state: 'triagem',
      priority: 'atencao',
      district: 'Flores',
      sourceType: 'comunidade',
      period: '7d',
      page: 3,
    }, new Date('2026-10-08T12:00:00-04:00'))

    expect(Object.fromEntries(search)).toEqual({
      page: '3',
      page_size: '6',
      query: 'febre',
      state: 'triage',
      priority_band: 'attention',
      district: 'Flores',
      source_kind: 'community',
      period_start: '2026-10-01',
    })
  })

  it('omite os filtros não selecionados', () => {
    expect(buildQueueSearch({ page: 1 }, new Date('2026-10-08T12:00:00-04:00')).toString()).toBe('page=1&page_size=6')
  })
})

describe('filtersFromSearchParams', () => {
  it('restaura os filtros canônicos da URL compartilhada', () => {
    expect(filtersFromSearchParams({
      page: '2',
      query: 'febre',
      state: 'verification',
      priority_band: 'routine',
      district: 'Flores',
      source_kind: 'media',
      period_start: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10),
    })).toMatchObject({
      page: 2,
      query: 'febre',
      state: 'verificacao',
      priority: 'monitorar',
      district: 'Flores',
      sourceType: 'midia',
      period: '7d',
    })
  })
})

describe('mapSignalDetail', () => {
  it('preserva a proveniência, ausências e sugestões do detalhe da API', () => {
    const detail = mapSignalDetail({
      signal,
      grouping: {
        identity_key: 'group-key',
        policy_version: 'grouping-v1',
        processing_state: 'ready',
        divergence_codes: ['location_conflict'],
      },
      sources: [
        {
          normalized_record_id: '9b2c3d4e-8f90-4ba1-9c2d-3e4f5a6b0042',
          role: 'core',
          source_kind: 'community',
          source_name: 'Canal sintético',
          published_at: '2026-10-07T10:00:00Z',
          title: null,
          excerpt: 'Relato sintético com febre.',
          technical_sheet: null,
        },
      ],
      relations: [
        {
          id: 'ab2c3d4e-8f90-4ba1-9c2d-3e4f5a6b0043',
          role: 'core',
          relation: 'corroborates',
          confidence: 0.82,
          justification: 'Mesmo distrito e sintomas.',
          method: 'relation-v1',
          state: 'succeeded',
        },
      ],
      audit_events: [],
    })

    expect(detail.signal.id).toBe(signal.id)
    expect(detail.signal.slug).toBe(signal.id)
    expect(detail.signal.priority).toBe('atencao')
    expect(detail.signal.divergences).toEqual(['location_conflict'])
    expect(detail.workflow).toEqual({ state: 'triagem', version: 2, updatedAt: '2026-10-07T12:00:00Z' })
    expect(detail.reviewTargets).toEqual([
      {
        type: 'grouping',
        id: signal.id,
        suggestionIdentityKey: 'group-key',
        label: 'Agrupamento sugerido',
      },
      {
        type: 'priority',
        id: signal.priority.id,
        suggestionIdentityKey: 'priority-key',
        label: 'Prioridade sugerida',
      },
    ])
    expect(detail.sources).toEqual(expect.arrayContaining([
      expect.objectContaining({
        id: '9b2c3d4e-8f90-4ba1-9c2d-3e4f5a6b0042',
        type: 'comunidade',
        title: 'Título não informado',
        sheet: null,
      }),
    ]))
    expect(detail.criteria).toEqual(expect.arrayContaining([
      expect.objectContaining({ label: 'Relação sugerida: corroborates', met: true }),
    ]))
  })
})
