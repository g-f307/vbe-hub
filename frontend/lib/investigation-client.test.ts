import { describe, expect, it } from 'vitest'

import {
  buildCompositionPayload,
  classifyInvestigationError,
  hideInvestigationMembers,
  mapInvestigation,
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
  it('mapeia explicitamente a cabeça e a projeção auditável da ficha', () => {
    expect(mapInvestigation({
      id: '018f6d5d-9c44-7b10-8000-000000000010',
      head_signal_id: '018f6d5d-9c44-7b10-8000-000000000001',
      version: 2,
      created_at: '2026-11-08T10:00:00Z',
      updated_at: '2026-11-08T10:05:00Z',
      members: [],
      events: [],
      technical_sheet: { symptoms: ['febre'] },
      technical_sheet_provenance: { symptoms: ['018f6d5d-9c44-7b10-8000-000000000001'] },
      technical_sheet_conflicts: [],
    })).toMatchObject({
      headSignalId: '018f6d5d-9c44-7b10-8000-000000000001',
      technicalSheet: { symptoms: ['febre'] },
      technicalSheetProvenance: { symptoms: ['018f6d5d-9c44-7b10-8000-000000000001'] },
    })
  })
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

  it('remove imediatamente da lista os sinais que a composição retornou como membros', () => {
    expect(hideInvestigationMembers([
      related('just-added', 'ready'),
      related('still-available', 'ready'),
    ], ['head', 'just-added']).map((item) => item.candidate.id)).toEqual(['still-available'])
  })

  it('classifica concorrência separadamente para orientar recarregamento', () => {
    expect(classifyInvestigationError(409, {
      code: 'investigation_version_conflict',
      current_version: 4,
    })).toMatchObject({ kind: 'conflict', currentVersion: 4 })
  })
})
