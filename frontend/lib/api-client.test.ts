import { describe, expect, it } from 'vitest'

import { resolveApiBaseUrl } from './api-client'

describe('resolveApiBaseUrl', () => {
  it('normaliza a URL pública da futura API', () => {
    expect(resolveApiBaseUrl('http://localhost:8000/')).toBe('http://localhost:8000')
  })

  it('rejeita credenciais em configuração destinada ao navegador', () => {
    expect(() => resolveApiBaseUrl('https://analista:segredo@api.example.test')).toThrow(
      'não pode conter credenciais',
    )
  })
})
