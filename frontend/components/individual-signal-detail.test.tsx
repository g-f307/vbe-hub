import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'

import { IndividualSignalDetailView } from './individual-signal-detail'
import type { IndividualSignalDetail, RelatedSignalPage } from '@/lib/individual-signal-read'

const signal: IndividualSignalDetail = {
  id: '018f6d5d-9c44-7b10-8000-000000000001',
  state: 'detected',
  createdAt: '2026-11-08T09:00:00Z',
  title: 'Relatos de febre e manchas no bairro',
  excerpt: 'Moradores relatam sintomas semelhantes.',
  sourceKind: 'community',
  sourceName: 'Guardiões da Saúde',
  publishedAt: '2026-11-08T08:00:00Z',
  activeInvestigationId: null,
  contractVersion: 'individual-signal-v1',
  source: {
    externalId: 'community-001',
    body: 'Texto original preservado do relato comunitário.',
    url: null,
    language: 'pt-BR',
  },
  provenance: {
    adapterName: 'synthetic-community',
    adapterVersion: '1.0',
    generatorName: 'vbe-hub',
    generatorVersion: '1.0',
    seed: 307,
    scenarioId: 'scenario-001',
    collectedAt: '2026-11-08T09:00:00Z',
  },
  technicalSheet: {
    disease_or_condition: 'Síndrome febril exantemática',
    symptoms: ['febre', 'manchas vermelhas'],
    location: { municipality: 'Manaus', district: 'Flores' },
  },
}

const related: RelatedSignalPage = {
  items: [
    {
      suggestionId: 'suggestion-ready',
      status: 'ready',
      updatedAt: '2026-11-08T09:05:00Z',
      errorCode: null,
      relation: 'corroborates',
      confidence: 0.88,
      justification: 'Mesmo local, período e sintomas.',
      candidate: { ...signal, id: 'candidate-ready', title: 'Notícia sobre sintomas em Flores' },
    },
    {
      suggestionId: 'suggestion-pending',
      status: 'pending',
      updatedAt: '2026-11-08T09:04:00Z',
      errorCode: null,
      relation: null,
      confidence: null,
      justification: null,
      candidate: { ...signal, id: 'candidate-pending', title: 'Relato aguardando análise' },
    },
    {
      suggestionId: 'suggestion-failed',
      status: 'failed',
      updatedAt: '2026-11-08T09:03:00Z',
      errorCode: 'provider_timeout',
      relation: null,
      confidence: null,
      justification: null,
      candidate: { ...signal, id: 'candidate-failed', title: 'Relato não processado' },
    },
  ],
  nextCursor: null,
}

describe('IndividualSignalDetailView', () => {
  it('preserva a fonte e apresenta relacionados como sugestões navegáveis', () => {
    const overview = renderToStaticMarkup(
      <IndividualSignalDetailView
        signal={signal}
        related={related}
        returnTo="/?state=detected&source_kind=community"
        activeTab="overview"
      />,
    )
    const suggestions = renderToStaticMarkup(
      <IndividualSignalDetailView
        signal={signal}
        related={related}
        returnTo="/?state=detected&source_kind=community"
        activeTab="related"
      />,
    )

    expect(overview).toContain('Texto original preservado do relato comunitário.')
    expect(overview).toContain('Ficha técnica')
    expect(overview).toContain('Sinais relacionados')
    expect(overview).toContain('href="/?state=detected&amp;source_kind=community"')
    expect(suggestions).toContain('Sugestões da IA não associam sinais automaticamente')
    expect(suggestions).toContain('Selecionar Notícia sobre sintomas em Flores')
    expect(suggestions).toContain('Criar ficha apenas com o sinal principal')
    expect(suggestions).toContain('A associação só será registrada após sua confirmação.')
    expect(suggestions).toContain('Mesmo local, período e sintomas.')
    expect(suggestions).toContain('Processamento em andamento')
    expect(suggestions).toContain('Não foi possível preparar esta sugestão')
    expect(suggestions).toContain('href="/sinais/candidate-ready?returnTo=')
  })
})
