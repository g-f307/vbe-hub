import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import { describe, expect, it } from 'vitest'

describe('identidade visual global', () => {
  it('expõe a paleta e a pilha tipográfica aprovadas', () => {
    const css = readFileSync(resolve(process.cwd(), 'app/globals.css'), 'utf8')

    expect(css).toContain('--brand-blue: #319ad3')
    expect(css).toContain('--brand-primary: #076ba4')
    expect(css).toContain('--brand-coral: #ff624e')
    expect(css).toContain('--brand-background: #f6f8fa')
    expect(css).toContain('"Geist", "Inter"')
  })

  it('mantém os ativos oficiais dentro do frontend reproduzível', () => {
    const logo = readFileSync(
      resolve(process.cwd(), 'public/brand/vbehub-horizontal-fundo-claro.svg'),
      'utf8',
    )
    const favicon = readFileSync(resolve(process.cwd(), 'public/brand/favicon.svg'), 'utf8')
    const darkHeaderLogo = readFileSync(
      resolve(process.cwd(), 'public/brand/vbehub-horizontal-fundo-escuro.svg'),
      'utf8',
    )

    expect(logo).toContain('<svg')
    expect(favicon).toContain('<svg')
    expect(darkHeaderLogo).toContain('<svg')
  })
})
