import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import { vi } from 'vitest'

vi.mock('next/navigation', () => ({ usePathname: () => '/panorama' }))

import { Header } from './header'

describe('Header', () => {
  it('usa a assinatura clara sobre o header azul e expõe a navegação centralizada sem textos auxiliares', () => {
    const html = renderToStaticMarkup(<Header />)

    expect(html).toContain('src="/brand/vbehub-horizontal-fundo-escuro.svg"')
    expect(html).toContain('alt="VBE Hub"')
    expect(html).not.toContain('Hub de Vigilância Baseada em Eventos')
    expect(html).not.toContain('Dados locais de demonstração')
    expect(html).toContain('href="/"')
    expect(html).toContain('Detectados')
    expect(html).toContain('href="/panorama"')
    expect(html).toContain('Visão geoespacial')
    expect(html).toContain('Indicadores')
    expect(html).not.toContain('Implementação futura')
    expect(html).toContain('justify-center')
    expect(html).not.toContain('rounded-b-')
    expect(html).toContain('pb-6')
    expect(html).toContain('aria-current="page"')
    expect(html).toContain('border-white text-white')
    expect(html).not.toContain('data-lucide="activity"')
  })
})
