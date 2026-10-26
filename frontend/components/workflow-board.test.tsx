import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'

import { WorkflowBoard } from './workflow-board'
import type { Signal, WorkflowState } from '@/lib/types'

function signal(id: string, state: WorkflowState, overrides: Partial<Signal> = {}): Signal {
  return {
    id,
    code: `VBE-${id}`,
    slug: id,
    title: `Sinal ${id}`,
    subtitle: 'Resumo do sinal',
    condition: 'Síndrome febril',
    symptoms: ['Febre', 'Exantema'],
    municipality: 'Manaus',
    neighborhood: 'Compensa',
    periodStart: '2026-10-01',
    periodEnd: '2026-10-03',
    magnitude: null,
    priority: 'atencao',
    priorityRationale: 'Sugestão automática sujeita à revisão humana.',
    state,
    createdAt: null,
    updatedAt: '2026-10-04T12:00:00Z',
    sourceIds: [],
    sourceCounts: { midia: 1, comunidade: 2, total: 3 },
    criteria: [],
    divergences: [],
    ...overrides,
  }
}

const signals = [
  signal('001', 'detectado'),
  signal('002', 'triagem'),
  signal('003', 'verificacao'),
  signal('004', 'avaliacao_risco'),
  signal('005', 'encerrado'),
]

describe('WorkflowBoard', () => {
  it('reconcilia cada sinal em uma única coluna do fluxo canônico', () => {
    const html = renderToStaticMarkup(<WorkflowBoard signals={signals} total={5} view="board" queryString="query=febre" />)

    expect(html).toContain('Detectados')
    expect(html).toContain('Em triagem')
    expect(html).toContain('Em verificação')
    expect(html).toContain('Avaliação de risco')
    expect(html).toContain('Encerrados')
    for (const item of signals) expect(html.match(new RegExp(`Sinal ${item.id}`, 'g'))).toHaveLength(1)
    expect(html).toContain('5 sinais exibidos de 5 encontrados')
  })

  it('mantém sugestões, proveniência e decisão humana explícitas no cartão', () => {
    const html = renderToStaticMarkup(<WorkflowBoard signals={[signals[1]]} total={1} view="board" queryString="" />)

    expect(html).toContain('Prioridade sugerida')
    expect(html).toContain('1 sinal exibido de 1 encontrado')
    expect(html).toContain('3 fontes')
    expect(html).toContain('Compensa')
    expect(html).toContain('1–3 out. 2026')
    expect(html).toContain('/sinais/002')
    expect(html).toContain('/sinais/002#decisao')
    expect(html).toContain('A decisão final é da vigilância')
    expect(html).not.toContain('draggable=')
  })

  it('oferece tabela acessível sem perder a consulta compartilhável', () => {
    const html = renderToStaticMarkup(<WorkflowBoard signals={signals.slice(0, 2)} total={2} view="list" queryString="district=Compensa" />)

    expect(html).toContain('<table')
    expect(html).toContain('Lista acessível do fluxo')
    expect(html).toContain('/kanban?district=Compensa&amp;view=board')
    expect(html).toContain('/triagem?district=Compensa')
  })

  it('explica colunas vazias e o limite da leitura', () => {
    const html = renderToStaticMarkup(<WorkflowBoard signals={[]} total={142} view="board" queryString="" limit={100} />)

    expect(html).toContain('Nenhum sinal neste estágio com os filtros atuais.')
    expect(html).toContain('A visão está limitada aos 100 primeiros de 142 sinais')
  })
})
