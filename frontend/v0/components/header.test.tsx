import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'

import { Header } from './header'

describe('Header', () => {
  it('usa a assinatura horizontal aprovada da VBE Hub', () => {
    const html = renderToStaticMarkup(<Header />)

    expect(html).toContain('src="/brand/vbehub-horizontal-fundo-claro.svg"')
    expect(html).toContain('alt="VBE Hub"')
    expect(html).toContain('Hub de Vigilância Baseada em Eventos')
    expect(html).not.toContain('data-lucide="activity"')
  })
})
