import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'

import { DetectedSignalsView } from './detected-signals'
import type { IndividualSignalCard } from '@/lib/individual-signal-read'

const items: IndividualSignalCard[] = [
  {
    id: 'signal-media',
    state: 'detected',
    createdAt: '2026-11-08T09:00:00Z',
    title: 'Jornal relata aumento de casos de sarampo',
    excerpt: 'Notícia sobre aumento de atendimentos no bairro Flores.',
    sourceKind: 'media',
    sourceName: 'Portal de notícias',
    publishedAt: '2026-11-08T08:00:00Z',
    activeInvestigationId: null,
  },
  {
    id: 'signal-community',
    state: 'detected',
    createdAt: '2026-11-08T09:01:00Z',
    title: 'Moradores relatam febre e manchas vermelhas',
    excerpt: 'Relato comunitário preservado como fonte independente.',
    sourceKind: 'community',
    sourceName: 'Guardiões da Saúde',
    publishedAt: '2026-11-08T08:05:00Z',
    activeInvestigationId: null,
  },
]

describe('DetectedSignalsView', () => {
  it('mantém cada fonte em um card e preserva o retorno e a paginação na URL', () => {
    const html = renderToStaticMarkup(
      <DetectedSignalsView
        items={items}
        nextCursor="cursor-2"
        filters={{ state: 'detected', sourceKind: 'community' }}
      />,
    )

    expect(html).toContain('Sinais detectados')
    expect(html).toContain('Jornal relata aumento de casos de sarampo')
    expect(html).toContain('Moradores relatam febre e manchas vermelhas')
    expect(html).toContain('>2</strong> sinais nesta página')
    expect(html).toContain('href="/sinais/signal-community?returnTo=')
    expect(html).toContain('cursor=cursor-2')
    expect(html).toContain('source_kind=community')
    expect(html).not.toContain('draggable="true"')
  })

  it('filtra textualmente o lote carregado sem fundir as fontes', () => {
    const html = renderToStaticMarkup(
      <DetectedSignalsView
        items={items}
        nextCursor={null}
        filters={{ state: 'detected', query: 'manchas vermelhas' }}
      />,
    )

    expect(html).toContain('Moradores relatam febre e manchas vermelhas')
    expect(html).not.toContain('Jornal relata aumento de casos de sarampo')
    expect(html).toContain('value="manchas vermelhas"')
    expect(html).toContain('query%3Dmanchas%2Bvermelhas')
  })
})
