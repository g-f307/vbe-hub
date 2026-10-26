import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'

import { PanoramaBoard } from './panorama-board'
import type { GeographicSummary } from '@/lib/panorama-read'

const summary: GeographicSummary = {
  datasetKind: 'synthetic',
  datasetIdentity: 'vbe-hub-synthetic-poc',
  window: { start: '2026-10-01', end: '2026-10-10' },
  updatedAt: '2026-10-10T12:00:00Z',
  totals: { signals: 3, mappedSignals: 2, unmappedSignals: 1, areas: 2 },
  areas: [
    {
      key: 'manaus--compensa',
      municipality: 'Manaus',
      district: 'Compensa',
      signals: 1,
      sourceCounts: { media: 1, community: 1, total: 2 },
      workflowStates: { detected: 1 },
      priorityBands: { prompt: 1 },
      topCondition: { label: 'Dengue', count: 1 },
    },
    {
      key: 'manaus--bairro-sem-geometria',
      municipality: 'Manaus',
      district: 'Bairro sem geometria',
      signals: 1,
      sourceCounts: { media: 0, community: 1, total: 1 },
      workflowStates: { verification: 1 },
      priorityBands: { routine: 1 },
      topCondition: null,
    },
  ],
}

describe('PanoramaBoard', () => {
  it('apresenta agregados reais, alternativa textual e filtro canônico da área', () => {
    const html = renderToStaticMarkup(<PanoramaBoard summary={summary} />)

    expect(html).toContain('>3</p>')
    expect(html).toContain('sinais no período')
    expect(html).toContain('>1</p>')
    expect(html).toContain('sem área agregável')
    expect(html).toContain('1–10 out. 2026')
    expect(html).toContain('Compensa')
    expect(html).toContain('Bairro sem geometria')
    expect(html).toContain('Geometria indisponível')
    expect(html).toContain('/triagem?district=Compensa')
    expect(html).toContain('Dados sintéticos de apoio à triagem')
  })

  it('orienta o carregamento quando ainda não há sinais consolidados', () => {
    const html = renderToStaticMarkup(
      <PanoramaBoard
        summary={{
          ...summary,
          totals: { signals: 0, mappedSignals: 0, unmappedSignals: 0, areas: 0 },
          window: { start: null, end: null },
          updatedAt: null,
          areas: [],
        }}
      />,
    )

    expect(html).toContain('Nenhum sinal consolidado para o panorama')
    expect(html).toContain('demo-load')
  })
})
