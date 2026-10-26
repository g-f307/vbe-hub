import { describe, expect, it } from 'vitest'

import { mapGeographicSummary } from './panorama-read'
import { geometryForArea } from './territory-geometry'

const response = {
  dataset_kind: 'synthetic',
  dataset_identity: 'vbe-hub-synthetic-poc',
  window: { start: '2026-10-01', end: '2026-10-10' },
  updated_at: '2026-10-10T12:00:00Z',
  totals: { signals: 4, mapped_signals: 3, unmapped_signals: 1, areas: 2 },
  areas: [
    {
      key: 'manaus--compensa',
      municipality: 'Manaus',
      district: 'Compensa',
      signals: 2,
      source_counts: { media: 2, community: 1, total: 3 },
      workflow_states: { detected: 1, triage: 1 },
      priority_bands: { prompt: 1, attention: 1 },
      top_condition: { label: 'Dengue', count: 2 },
    },
    {
      key: 'manaus--bairro-sem-geometria',
      municipality: 'Manaus',
      district: 'Bairro sem geometria',
      signals: 1,
      source_counts: { media: 0, community: 1, total: 1 },
      workflow_states: { verification: 1 },
      priority_bands: { routine: 1 },
      top_condition: null,
    },
  ],
}

describe('mapGeographicSummary', () => {
  it('converte o agregado territorial sem introduzir dados individuais', () => {
    const summary = mapGeographicSummary(response)

    expect(summary).toEqual({
      datasetKind: 'synthetic',
      datasetIdentity: 'vbe-hub-synthetic-poc',
      window: { start: '2026-10-01', end: '2026-10-10' },
      updatedAt: '2026-10-10T12:00:00Z',
      totals: { signals: 4, mappedSignals: 3, unmappedSignals: 1, areas: 2 },
      areas: [
        {
          key: 'manaus--compensa',
          municipality: 'Manaus',
          district: 'Compensa',
          signals: 2,
          sourceCounts: { media: 2, community: 1, total: 3 },
          workflowStates: { detected: 1, triage: 1 },
          priorityBands: { prompt: 1, attention: 1 },
          topCondition: { label: 'Dengue', count: 2 },
        },
        {
          key: 'manaus--bairro-sem-geometria',
          municipality: 'Manaus',
          district: 'Bairro sem geometria',
          signals: 1,
          sourceCounts: { media: 0, community: 1, total: 1 },
          workflowStates: { verification: 1 },
          priorityBands: { routine: 1 },
          topCondition: null,
        },
      ],
    })
  })

  it('rejeita respostas sem a identificação sintética obrigatória', () => {
    expect(() => mapGeographicSummary({ ...response, dataset_kind: 'unknown' })).toThrow(
      'resumo territorial em formato inválido',
    )
  })
})

describe('geometryForArea', () => {
  it('resolve geometria local somente para áreas versionadas', () => {
    expect(geometryForArea('Manaus', 'Compensa')?.version).toBe('demo-areas-v1')
    expect(geometryForArea('Manaus', 'Bairro sem geometria')).toBeNull()
  })
})
