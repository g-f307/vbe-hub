import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it, vi } from 'vitest'

import { SignalCard } from './signal-card'
import type { Signal } from '@/v0/lib/types'

const signal: Signal = {
  id: 'signal-1',
  title: 'Relato comunitário de síndrome febril',
  description: 'Descrição para demonstração.',
  status: 'informado',
  riskLevel: 'medio',
  source: 'Guardiões da Saúde',
  signalType: 'Abertura',
  confidentiality: 'Nível 1',
  tags: ['febre'],
  countries: ['Brasil'],
  states: ['Amazonas'],
  municipalities: ['Manaus'],
  signalDate: '2026-11-08T08:00:00Z',
  detectionDate: '2026-11-08T09:00:00Z',
  createdAt: '2026-11-08T09:00:00Z',
  updatedAt: '2026-11-08T09:00:00Z',
}

describe('SignalCard', () => {
  it('navega para a página dedicada do sinal por um link acessível', () => {
    const html = renderToStaticMarkup(
      <SignalCard
        signal={signal}
        href="/sinais/signal-1?returnTo=%2F%3Fsource_kind%3Dcommunity"
        onClick={vi.fn()}
        onDragStart={vi.fn()}
      />,
    )

    expect(html).toContain('<a')
    expect(html).toContain('href="/sinais/signal-1?returnTo=%2F%3Fsource_kind%3Dcommunity"')
    expect(html).toContain('aria-label="Abrir sinal Relato comunitário de síndrome febril"')
  })
})
