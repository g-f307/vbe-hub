import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'

import { Header } from './header'

describe('Header', () => {
  it('usa a assinatura clara sobre o header azul e expõe as visões previstas', () => {
    const html = renderToStaticMarkup(<Header />)

    expect(html).toContain('src="/brand/vbehub-horizontal-fundo-escuro.svg"')
    expect(html).toContain('alt="VBE Hub"')
    expect(html).toContain('Hub de Vigilância Baseada em Eventos')
    expect(html).toContain('href="/"')
    expect(html).toContain('Detectados')
    expect(html).toContain('href="/panorama"')
    expect(html).toContain('Visão geoespacial')
    expect(html).toContain('Indicadores')
    expect(html).toContain('Implementação futura')
    expect(html).not.toContain('data-lucide="activity"')
  })
})
