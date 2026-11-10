import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it, vi } from 'vitest'

vi.mock('@/lib/panorama-read', () => ({
  getGeographicSummary: vi.fn().mockResolvedValue({
    generatedAt: '2026-11-08T12:00:00Z',
    totals: { signals: 0, mediaSources: 0, communitySources: 0, investigations: 0 },
    areas: [],
  }),
}))

import PanoramaPage from './page'

describe('PanoramaPage', () => {
  it('preserva o header institucional ao abrir a visão geoespacial', async () => {
    const html = renderToStaticMarkup(await PanoramaPage())

    expect(html).toContain('src="/brand/vbehub-horizontal-fundo-escuro.svg"')
    expect(html).toContain('Visão geoespacial')
    expect(html).toContain('rounded-t-3xl')
    expect(html).toContain('-mt-6')
  })
})
