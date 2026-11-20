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
    const navigation = html.slice(html.indexOf('<nav'), html.indexOf('</nav>'))
    expect(navigation).toContain('text-[15px] font-semibold')
    expect(navigation).toContain('border-b-[3px]')
    expect(navigation).toContain('text-shadow:0_1px_1px_')
    expect(navigation).toContain('stroke-width="2.25"')
    expect(navigation).not.toContain('bg-white/')
    expect(html).toContain('border-white/35')
    expect(html).not.toContain('bg-primary')
    expect(html).toContain('text-white')
    expect(html).not.toContain('text-[#102E40]')
    expect(html).not.toContain('data-lucide="activity"')
  })
})
