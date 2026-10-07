import { describe, expect, it } from 'vitest'
import { resolveApiBaseUrl } from './api'

describe('resolveApiBaseUrl', () => {
  it('normaliza uma base HTTP pública para o cliente do painel', () => {
    expect(resolveApiBaseUrl('http://localhost:8000/')).toBe('http://localhost:8000')
  })

  it('rejeita URL com credenciais para não expor segredo no bundle', () => {
    expect(() => resolveApiBaseUrl('https://analista:segredo@api.example.test')).toThrow(
      'não pode conter credenciais',
    )
  })
})
