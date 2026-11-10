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
    expect(html).not.toContain('Entrada da vigilância')
    expect(html).toContain('text-[26px]')
    expect(html).toContain('Jornal relata aumento de casos de sarampo')
    expect(html).toContain('Moradores relatam febre e manchas vermelhas')
    expect(html).toContain('>Mídia</p>')
    expect(html).toContain('>Relato comunitário</p>')
    expect(html).not.toContain('data-slot="badge"')
    expect(html).not.toContain('>Portal de notícias</p>')
    expect(html).not.toContain('>Guardiões da Saúde</p>')
    expect(html).not.toContain('sinais nesta página')
    expect(html).toContain('href="/sinais/signal-community?returnTo=')
    expect(html).toContain('cursor=cursor-2')
    expect(html).toContain('source_kind=community')
    expect(html).not.toContain('draggable="true"')
    expect(html).toContain('data-state-banner="detected"')
    expect(html).toContain('data-layered-card="true"')
    expect(html).toContain('data-progress-outline="true"')
    expect(html).toContain('[clip-path:inset(0_0_50%_0)]')
    expect(html).toContain('bg-[#3E6F9E]')
    expect(html).toContain('border-[#3E6F9E]')
    expect(html).not.toContain('border-blue-600')
    expect(html).toContain('xl:grid-cols-3')
    expect(html).toContain('gap-x-8')
    expect(html).toContain('gap-y-6')
    expect(html).toContain('max-w-[1280px]')
    expect(html).toContain('min-h-[285px]')
    expect(html).not.toContain('xl:aspect-[1.15/1]')
    expect(html).toContain('rounded-t-xl')
    expect(html).toContain('>Detectado</span>')
    expect(html).not.toContain('data-state-badge="detected"')
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

  it('mantém a convenção cromática sóbria definida para os estágios do fluxo', () => {
    const states = ['detected', 'triage', 'verification', 'risk_assessment', 'closed'] as const
    const html = renderToStaticMarkup(
      <DetectedSignalsView
        items={states.map((state, index) => ({ ...items[0], id: `signal-${state}`, state, title: `Sinal ${index}` }))}
        nextCursor={null}
        filters={{ state: 'all', view: 'cards' }}
      />,
    )

    expect(html).toContain('bg-[#3E6F9E]')
    expect(html).toContain('bg-[#47735F]')
    expect(html).toContain('bg-[#A47B32]')
    expect(html).toContain('bg-[#A6534D]')
    expect(html).toContain('bg-[#626970]')
  })

  it.each([
    ['cards', 'Lista de sinais'],
    ['list', 'Sinais em lista'],
    ['kanban', 'Quadro Kanban dos sinais'],
  ] as const)('seleciona a visualização %s fora do formulário de filtros', (view, landmark) => {
    const html = renderToStaticMarkup(
      <DetectedSignalsView
        items={items}
        nextCursor={null}
        filters={{ state: 'all', sourceKind: 'community', query: 'febre', view }}
      />,
    )

    expect(html).toContain('aria-label="Selecionar visualização"')
    expect(html).toContain('data-close-on-outside="true"')
    expect(html).toContain(`data-view="${view}"`)
    expect(html).toContain(landmark)
    expect(html).not.toContain('>Visualização</p>')
    expect(html).not.toContain('aria-label="Modo de visualização"')
    expect(html.indexOf('</form>')).toBeLessThan(html.indexOf('aria-label="Selecionar visualização"'))
  })

  it('apresenta a lista como tabela compacta com marca cromática do estágio', () => {
    const html = renderToStaticMarkup(
      <DetectedSignalsView items={items} nextCursor={null} filters={{ state: 'all', view: 'list' }} />,
    )

    expect(html).toContain('Sinal</span>')
    expect(html).toContain('Fonte</span>')
    expect(html).not.toContain('Origem</span>')
    expect(html).toContain('Publicação</span>')
    expect(html).toContain('Etapa</span>')
    expect(html).toContain('lucide-users-round')
    expect(html).toContain('Relato comunitário</span>')
    expect(html).toContain('data-state-row="detected"')
    expect(html).toContain('data-state-marker="detected"')
    expect(html).toContain('top-3 bottom-3')
    expect(html).not.toContain('border-l-[#3E6F9E]')
    expect(html).toContain('data-source-label="community"')
  })

  it('usa no Kanban cards compactos com uma faixa cromática sem repetir o nome da etapa', () => {
    const html = renderToStaticMarkup(
      <DetectedSignalsView items={items} nextCursor={null} filters={{ state: 'all', view: 'kanban' }} />,
    )

    expect(html).toContain('data-kanban-state-stripe="detected"')
    expect(html).not.toContain('data-layered-card="kanban"')
    expect(html).not.toContain('data-progress-outline="kanban"')
    expect(html).not.toContain('data-state-banner="detected"')
    expect(html).toContain('min-h-[190px]')
    expect(html).toContain('>Mídia</p>')
    expect(html).toContain('>Relato comunitário</p>')
  })
})
