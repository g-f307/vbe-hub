import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'

import { IndividualSignalDetailView } from './individual-signal-detail'
import type { IndividualSignalDetail, InvestigationDetail, RelatedSignalPage } from '@/lib/individual-signal-read'

const signal: IndividualSignalDetail = {
  id: '018f6d5d-9c44-7b10-8000-000000000001',
  state: 'detected',
  createdAt: '2026-11-08T09:00:00Z',
  title: 'Relatos de febre e manchas no bairro',
  excerpt: 'Moradores relatam sintomas semelhantes.',
  sourceKind: 'community',
  sourceName: 'demo-community',
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
      justification: 'Mesmo local, período e sintomas. Os registros descrevem fontes independentes com informações compatíveis que devem ser comparadas integralmente pelo analista.',
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

const investigation: InvestigationDetail = {
  id: '018f6d5d-9c44-7b10-8000-000000000010',
  headSignalId: signal.id,
  version: 2,
  createdAt: '2026-11-08T09:00:00Z',
  updatedAt: '2026-11-08T09:10:00Z',
  technicalSheet: { ...(signal.technicalSheet ?? {}), estimated_cases: 4 },
  technicalSheetProvenance: { estimated_cases: ['candidate-ready'] },
  technicalSheetConflicts: [],
  members: [
    { addedAt: '2026-11-08T09:00:00Z', addedBy: 'analyst', signal },
    {
      addedAt: '2026-11-08T09:10:00Z',
      addedBy: 'analyst',
      signal: {
        ...signal,
        id: 'candidate-ready',
        title: 'Notícia sobre sintomas em Flores',
        sourceKind: 'media',
        source: { ...signal.source, body: 'Quatro pacientes foram atendidos com sintomas semelhantes.' },
      },
    },
  ],
  events: [],
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
    expect(overview).toContain('Relacionar sinais')
    expect(overview).toContain('data-detail-layout="investigation-workspace"')
    expect(overview).toContain('data-detail-header="signal-record"')
    expect(overview).toContain('data-signal-facts="true"')
    expect(overview).toContain('data-overview-layout="reading-and-context"')
    expect(overview).toContain('data-overview-dashboard="true"')
    expect(overview).toContain('lg:grid-cols-12')
    expect(overview).toContain('data-workspace-tabs="true"')
    expect(overview).toContain('left-1/2 top-full w-fit')
    expect(overview).toContain('w-max')
    expect(overview).not.toContain('-translate-y-1/2')
    expect(overview).toContain('data-detail-chrome="header-and-tabs"')
    expect(overview).toContain('data-text-position="side"')
    expect(overview).toContain('data-context-position="full"')
    expect(overview).toContain('lg:col-span-4')
    expect(overview).toContain('lg:col-span-8')
    expect(overview).toContain('Analisar sinal')
    expect(overview).toContain('Relacionar sinais')
    expect(overview).not.toContain('Rastrear origem')
    expect(overview).not.toContain('demo-community')
    expect(overview.match(/Relato comunitário/g)).toHaveLength(1)
    expect(overview.match(/Relacionar sinais/g)).toHaveLength(1)
    expect(overview).not.toContain('Ver possíveis relações')
    expect(overview).toContain('bg-card text-primary shadow-sm')
    expect(overview).toContain('data-panel-tone="card"')
    expect(overview).not.toContain('data-signal-state="detected"')
    expect(overview).toContain('data-technical-state="detected"')
    expect(overview).toContain('flex items-center gap-3')
    expect(overview).not.toContain('items-center text-center')
    expect(overview).not.toContain('data-context-badge="true"')
    expect(overview).toContain('data-technical-item="true"')
    expect(overview).not.toContain('data-technical-icon-tile="true"')
    expect(overview).not.toContain('overflow-hidden rounded-xl border border-border bg-card shadow-sm')
    expect(overview).not.toContain('Registro individual')
    expect(overview).not.toContain(`ID ${signal.id}`)
    expect(overview).not.toContain('Identificador externo')
    expect(overview).not.toContain('Decisão humana')
    expect(overview).not.toContain('Este registro apoia a investigação')
    expect(overview).toContain('href="/?state=detected&amp;source_kind=community"')
    expect(suggestions).toContain('Sugestões da IA não associam sinais automaticamente')
    expect(suggestions).toContain('Selecionar sinal')
    expect(suggestions).toContain('data-candidate-card="kanban"')
    expect(suggestions).toContain('Possível relação')
    expect(suggestions).not.toContain('confiança técnica')
    expect(suggestions).toContain('Ler mais')
    expect(suggestions).not.toContain('Decisão de composição')
    expect(suggestions).not.toContain('Criar ficha apenas com o sinal principal')
    expect(suggestions).not.toContain('Revisar composição')
    expect(suggestions).not.toContain('Confirmar composição da ficha')
    expect(suggestions).toContain('Mesmo local, período e sintomas.')
    expect(suggestions).toContain('Processamento em andamento')
    expect(suggestions).toContain('Não foi possível preparar esta sugestão')
    expect(suggestions).toContain('href="/sinais/candidate-ready?returnTo=')
  })

  it('omite campos internos da ficha técnica sem alterar os campos epidemiológicos úteis', () => {
    const withInternalFields: IndividualSignalDetail = {
      ...signal,
      technicalSheet: {
        ...(signal.technicalSheet ?? {}),
        evidence: 'field: symptoms · excerpt: febre',
        confidence: 0.98,
        record_nature: 'community',
        action_in_progress: null,
        suggested_relevance: null,
      },
    }
    const html = renderToStaticMarkup(
      <IndividualSignalDetailView signal={withInternalFields} related={related} returnTo="/" activeTab="overview" />,
    )

    expect(html).toContain('Condição mencionada')
    expect(html).toContain('Sintomas')
    expect(html).not.toContain('field: symptoms')
    expect(html).not.toContain('>confidence<')
    expect(html).not.toContain('>record nature<')
    expect(html).not.toContain('>action in progress<')
    expect(html).not.toContain('>suggested relevance<')
  })

  it('mantém a cabeça na análise e separa evidências já vinculadas dos candidatos inéditos', () => {
    const overview = renderToStaticMarkup(
      <IndividualSignalDetailView signal={signal} related={{ items: [], nextCursor: null }} returnTo="/" activeTab="overview" initialInvestigation={investigation} />,
    )
    const evidence = renderToStaticMarkup(
      <IndividualSignalDetailView signal={signal} related={{ items: [], nextCursor: null }} returnTo="/" activeTab="evidence" initialInvestigation={investigation} />,
    )

    expect(overview).toContain('Evidências incorporadas')
    expect(overview).toContain('Notícia sobre sintomas em Flores')
    expect(overview).toContain('Quatro pacientes foram atendidos')
    expect(overview).toContain('Quantidade mencionada')
    expect(overview).toContain('Gerenciar evidências')
    expect(overview).toContain('data-overview-side-stack="true"')
    expect(overview).toContain('grid-rows-2')
    expect(overview).toContain('data-evidence-timeline="true"')
    expect(overview).toContain('data-evidence-card="incorporated"')
    expect(overview).toContain('border-t-[#75627F]')
    expect(overview).toContain('Incorporado em')
    expect(overview).toContain('Ver detalhes')
    expect(overview).not.toContain('>Evidência incorporada<')
    expect(overview).toContain('href="/sinais/candidate-ready?returnTo=')
    expect(evidence).toContain('Remover evidência')
    expect(evidence).toContain('Ver detalhes')
    expect(evidence).toContain('data-evidence-timeline="true"')
    expect(evidence).toContain('data-evidence-card="incorporated"')
    expect(evidence).toContain('border-t-[#75627F]')
    expect(evidence).toContain('data-evidence-layout="grid"')
    expect(evidence).not.toContain('Conteúdos preservados e vinculados por decisão humana')
    expect(evidence).not.toContain('Histórico da composição')
    expect(evidence).not.toContain('Remover da ficha')
  })

  it('mantém a ficha própria da evidência acessível somente para consulta', () => {
    const evidenceSignal = investigation.members[1].signal
    const html = renderToStaticMarkup(
      <IndividualSignalDetailView
        signal={evidenceSignal}
        related={{ items: [], nextCursor: null }}
        returnTo={`/sinais/${signal.id}?tab=evidence`}
        activeTab="overview"
        initialInvestigation={investigation}
      />,
    )

    expect(html).toContain('Somente consulta')
    expect(html).toContain('Quatro pacientes foram atendidos com sintomas semelhantes.')
    expect(html).not.toContain('Quantidade mencionada')
    expect(html).not.toContain('Relacionar sinais')
    expect(html).not.toContain('Gerenciar evidências')
  })
})
