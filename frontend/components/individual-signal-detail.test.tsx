import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import { IndividualSignalDetailView } from './individual-signal-detail'
import type {
  IndividualSignalDetail,
  InvestigationDetail,
  RelatedSignalPage,
} from '@/lib/individual-signal-read'

const signal: IndividualSignalDetail = {
  id: 'head',
  state: 'detected',
  createdAt: '2026-11-08T09:00:00Z',
  title: 'Relatos de febre no bairro',
  excerpt: 'Descrição preservada.',
  sourceKind: 'community',
  sourceName: 'demo-community',
  publishedAt: '2026-11-08T08:00:00Z',
  activeInvestigationId: null,
  contractVersion: 'individual-signal-v1',
  source: {
    externalId: 'community-001',
    body: 'Texto integral da comunidade.',
    url: null,
    language: 'pt-BR',
  },
  provenance: {
    adapterName: 'test',
    adapterVersion: '1',
    generatorName: null,
    generatorVersion: null,
    seed: null,
    scenarioId: null,
    collectedAt: '2026-11-08T09:00:00Z',
  },
  technicalSheet: {
    disease_or_condition: 'Dengue (suspeita)',
    symptoms: ['febre'],
    estimated_cases: 4,
    location: { district: 'Flores' },
    pathogen: 'não exibir',
    temporal: { start: '2026-11-01' },
    confidence: 0.99,
  },
}
const evidence = {
  ...signal,
  id: 'evidence',
  title: 'Outra fonte incorporada',
  source: { ...signal.source, body: 'Descrição própria da evidência.' },
}
const investigation: InvestigationDetail = {
  id: 'file',
  headSignalId: 'head',
  version: 2,
  createdAt: signal.createdAt,
  updatedAt: signal.createdAt,
  technicalSheet: { ...signal.technicalSheet },
  technicalSheetProvenance: {},
  technicalSheetConflicts: [],
  members: [
    { signal, addedAt: signal.createdAt, addedBy: 'analyst' },
    { signal: evidence, addedAt: signal.createdAt, addedBy: 'analyst' },
  ],
  events: [],
}
const related: RelatedSignalPage = {
  items: [
    {
      suggestionId: 'one',
      status: 'ready',
      relation: 'corroborates',
      candidate: { ...signal, id: 'new' },
      updatedAt: signal.createdAt,
      errorCode: null,
      confidence: 0.8,
      justification: 'Possível relação entre as fontes.',
    },
    {
      suggestionId: 'two',
      status: 'ready',
      relation: 'unrelated',
      candidate: { ...signal, id: 'unrelated' },
      updatedAt: signal.createdAt,
      errorCode: null,
      confidence: 0.9,
      justification: 'Não relacionados.',
    },
    {
      suggestionId: 'three',
      status: 'pending',
      relation: null,
      candidate: { ...signal, id: 'pending' },
      updatedAt: signal.createdAt,
      errorCode: null,
      confidence: null,
      justification: null,
    },
  ],
  nextCursor: null,
}

describe('detalhe do sinal', () => {
  it('exibe somente os dez campos aprovados e preserva o texto original como Descrição', () => {
    const html = renderToStaticMarkup(
      <IndividualSignalDetailView
        signal={signal}
        related={related}
        returnTo="/?cursor=page2"
        activeTab="overview"
      />,
    )
    for (const label of [
      'Confidencialidade',
      'Tipo de sinal',
      'Etiologia',
      'Perigo geral',
      'Perigo específico',
      'Etiquetas',
      'Data do sinal',
      'Data de detecção',
      'Data de notificação',
      'Descrição',
    ])
      expect(html).toContain(label)
    expect(html.match(/data-information-field=/g)).toHaveLength(9)
    for (const label of [
      '>Etapa<',
      '>Sintomas<',
      '>Síndrome<',
      '>Localização<',
      '>Patógeno<',
      '>Ambiente<',
      '>Grupo afetado<',
      '>Quantidade mencionada<',
      '>Óbitos estimados<',
      'Texto original da fonte',
    ])
      expect(html).not.toContain(label)
    expect(html).toContain('Texto integral da comunidade.')
    expect(html).toContain('Dengue (suspeita)')
    expect(html).toContain('01/11/2026')
    expect(html).toContain('Não informado')
  })

  it('tem duas abas e o botão contextual conta somente candidatos válidos', () => {
    const html = renderToStaticMarkup(
      <IndividualSignalDetailView
        signal={signal}
        related={related}
        returnTo="/"
        activeTab="evidence"
        initialInvestigation={investigation}
      />,
    )
    expect(html).toContain('Informações')
    expect(html).toContain('Sinais relacionados')
    expect(html).toContain('Possíveis sinais relacionados')
    expect(html).toContain('aria-label="1 disponíveis"')
    expect(html).not.toContain('Analisar sinal')
    expect(html).not.toContain('Gerenciar evidências')
    expect(html).toContain('Outra fonte incorporada')
    expect(html).toContain('Remover evidência')
    expect(html).toContain('aria-haspopup="dialog"')
  })

  it('consulta o incorporado com sua própria ficha e retorna à aba e à página da fila', () => {
    const queue = '/?view=list&cursor=page2&state=triage'
    const headReturn = `/sinais/head?${new URLSearchParams({ tab: 'evidence', returnTo: queue })}`
    const html = renderToStaticMarkup(
      <IndividualSignalDetailView
        signal={evidence}
        related={related}
        returnTo={headReturn}
        activeTab="overview"
        initialInvestigation={investigation}
      />,
    )
    expect(html).toContain('Somente consulta')
    expect(html).toContain('Voltar ao sinal principal')
    expect(html).toContain('Descrição própria da evidência.')
    expect(html).toContain(
      'href="/?view=list&amp;cursor=page2&amp;state=triage"',
    )
    expect(html).toContain('tab=evidence')
    expect(html).not.toContain('Possíveis sinais relacionados')
    expect(html).not.toContain('Remover evidência')
  })

  it('distingue ausência de candidatos de falha na leitura das sugestões', () => {
    const props = { signal, related: { items: [], nextCursor: null }, returnTo: '/', activeTab: 'evidence' as const }
    const empty = renderToStaticMarkup(<IndividualSignalDetailView {...props} />)
    expect(empty).toContain('aria-label="0 disponíveis"')
    expect(empty).toContain('Ainda não há evidências incorporadas')
    const unavailable = renderToStaticMarkup(<IndividualSignalDetailView {...props} relatedUnavailable />)
    expect(unavailable).toContain('Não foi possível carregar as sugestões')
    expect(unavailable).toContain('Tentar novamente')
    expect(unavailable).toContain('disabled')
  })

  it('preserva a divisão lateral quando há incorporados e a altura integral sem eles', () => {
    const withEvidence = renderToStaticMarkup(
      <IndividualSignalDetailView
        signal={signal}
        related={related}
        returnTo="/?cursor=page2"
        activeTab="overview"
        initialInvestigation={investigation}
      />,
    )
    const alone = renderToStaticMarkup(
      <IndividualSignalDetailView
        signal={signal}
        related={related}
        returnTo="/"
        activeTab="overview"
      />,
    )
    expect(withEvidence).toContain('grid-rows-2')
    expect(withEvidence).toContain('Incorporado em')
    expect(withEvidence).toContain('returnTo%3D%252F%253Fcursor%253Dpage2')
    expect(alone).not.toContain('grid-rows-2')
  })
})
