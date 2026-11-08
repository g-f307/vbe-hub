import { describe, expect, it } from 'vitest'

import {
  buildCompositionPayload,
  classifyInvestigationError,
  selectableRelatedSignals,
} from './investigation-client'
import type { RelatedSignal } from './individual-signal-read'

const related = (id: string, status: RelatedSignal['status'], activeInvestigationId: string | null = null): RelatedSignal => ({
  suggestionId: `suggestion-${id}`,
  status,
  updatedAt: '2026-11-08T10:00:00Z',
  errorCode: null,
  relation: status === 'ready' ? 'corroborates' : null,
  confidence: status === 'ready' ? 0.9 : null,
  justification: status === 'ready' ? 'Mesmo local, período e sintomas.' : null,
  candidate: {
    id,
    state: 'detected',
    createdAt: '2026-11-08T09:00:00Z',
    title: `Sinal ${id}`,
    excerpt: 'Descrição individual preservada.',
    sourceKind: 'media',
    sourceName: 'Fonte de teste',
    publishedAt: '2026-11-08T08:00:00Z',
    activeInvestigationId,
  },
})

describe('investigation composition', () => {
  it('envia somente IDs únicos confirmados e não envia identidade do analista', () => {
    expect(buildCompositionPayload({
      primarySignalId: '018f6d5d-9c44-7b10-8000-000000000001',
      selectedSignalIds: [
        '018f6d5d-9c44-7b10-8000-000000000002',
        '018f6d5d-9c44-7b10-8000-000000000002',
        '018f6d5d-9c44-7b10-8000-000000000003',
      ],
      operationKey: 'compose-test-001',
    })).toEqual({
      primary_signal_id: '018f6d5d-9c44-7b10-8000-000000000001',
      selected_signal_ids: [
        '018f6d5d-9c44-7b10-8000-000000000002',
        '018f6d5d-9c44-7b10-8000-000000000003',
      ],
      operation_key: 'compose-test-001',
    })
  })

  it('oferece para seleção apenas sugestões prontas e ainda sem outra ficha', () => {
    expect(selectableRelatedSignals([
      related('ready-free', 'ready'),
      related('pending', 'pending'),
      related('failed', 'failed'),
      related('ready-assigned', 'ready', 'existing-file'),
    ]).map((item) => item.candidate.id)).toEqual(['ready-free'])
  })

  it('classifica concorrência separadamente para orientar recarregamento', () => {
    expect(classifyInvestigationError(409, {
      code: 'investigation_version_conflict',
      current_version: 4,
    })).toMatchObject({ kind: 'conflict', currentVersion: 4 })
  })
})
