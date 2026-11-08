import { describe, expect, it } from 'vitest'

import { safeInternalReturnTo } from './safe-navigation'

describe('safeInternalReturnTo', () => {
  it('preserva apenas destinos internos da fila', () => {
    expect(safeInternalReturnTo('/?state=detected&source_kind=community')).toBe('/?state=detected&source_kind=community')
    expect(safeInternalReturnTo('https://example.com')).toBe('/')
    expect(safeInternalReturnTo('//example.com')).toBe('/')
    expect(safeInternalReturnTo(undefined)).toBe('/')
  })
})
