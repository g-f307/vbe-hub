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
  it('expõe o cartão como controle acessível por teclado', () => {
    const html = renderToStaticMarkup(
      <SignalCard signal={signal} onClick={vi.fn()} onDragStart={vi.fn()} />,
    )

    expect(html).toContain('role="button"')
    expect(html).toContain('tabindex="0"')
    expect(html).toContain('aria-label="Abrir sinal Relato comunitário de síndrome febril"')
  })
})
