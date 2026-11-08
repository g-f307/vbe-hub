import { describe, expect, it } from 'vitest'

import { parseDetectedFilters } from './page'

describe('filtros da fila de detectados', () => {
  it('restaura filtros válidos da URL e usa detected como entrada padrão', () => {
    expect(parseDetectedFilters({
      state: 'triage',
      source_kind: 'community',
      query: '  febre  ',
      cursor: 'cursor-2',
    })).toEqual({
      state: 'triage',
      sourceKind: 'community',
      query: 'febre',
      cursor: 'cursor-2',
    })

    expect(parseDetectedFilters({ state: 'invalido', source_kind: 'invalida' })).toEqual({
      state: 'detected',
      sourceKind: 'all',
      query: undefined,
      cursor: undefined,
    })
  })
})
