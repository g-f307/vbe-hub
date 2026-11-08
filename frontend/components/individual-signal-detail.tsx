import Link from 'next/link'
import {
  ArrowLeft,
  CalendarClock,
  Clock3,
  ExternalLink,
  FileText,
  Link2,
  MapPin,
  Newspaper,
  Radio,
  ShieldCheck,
} from 'lucide-react'

import type {
  IndividualSignalDetail,
  IndividualSignalState,
  InvestigationDetail,
  RelatedSignalPage,
  SignalAuditEvent,
} from '@/lib/individual-signal-read'
import { InvestigationComposer } from '@/components/investigation-composer'
import { Badge } from '@/v0/components/ui/badge'
import { Card } from '@/v0/components/ui/card'

type DetailTab = 'overview' | 'related' | 'provenance'

export function IndividualSignalDetailView({
  signal,
  related,
  audit = [],
  returnTo,
  activeTab,
  initialInvestigation = null,
}: {
  signal: IndividualSignalDetail
  related: RelatedSignalPage
  audit?: SignalAuditEvent[]
  returnTo: string
  activeTab: DetailTab
  initialInvestigation?: InvestigationDetail | null
}) {
  return (
    <main id="conteudo-principal" className="mx-auto w-full max-w-screen-xl px-4 py-6 sm:px-6 lg:px-8">
      <Link
        href={returnTo}
        className="mb-5 inline-flex min-h-11 items-center gap-2 rounded-md px-2 text-sm font-medium text-primary hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        <ArrowLeft className="size-4" aria-hidden />
        Voltar para detectados
      </Link>

      <section className="overflow-hidden rounded-xl border border-border bg-card shadow-sm">
        <div className="border-b border-border bg-primary px-5 py-5 text-primary-foreground sm:px-7">
          <div className="flex flex-wrap items-center gap-2 text-xs text-primary-foreground/80">
            <Badge className="border-primary-foreground/30 bg-primary-foreground/10 text-primary-foreground">
              {SOURCE_LABEL[signal.sourceKind]}
            </Badge>
            <span>{signal.sourceName}</span>
            <span aria-hidden>•</span>
            <span>{formatDate(signal.publishedAt)}</span>
          </div>
          <div className="mt-3 flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <div className="max-w-4xl">
              <p className="font-mono text-xs text-primary-foreground/70">{signal.id}</p>
              <h1 className="mt-1 text-balance text-2xl font-semibold leading-tight sm:text-3xl">{signal.title}</h1>
              <p className="mt-2 max-w-3xl text-sm leading-relaxed text-primary-foreground/80">{signal.excerpt}</p>
            </div>
            <StateBadge state={signal.state} />
          </div>
        </div>

        <nav aria-label="Seções do sinal" className="flex overflow-x-auto border-b border-border px-3 sm:px-5">
          <TabLink signalId={signal.id} returnTo={returnTo} tab="overview" active={activeTab === 'overview'}>
            Visão geral
          </TabLink>
          <TabLink signalId={signal.id} returnTo={returnTo} tab="related" active={activeTab === 'related'}>
            Sinais relacionados
            <span className="ml-1.5 rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground">{related.items.length}</span>
          </TabLink>
          <TabLink signalId={signal.id} returnTo={returnTo} tab="provenance" active={activeTab === 'provenance'}>
            Proveniência
          </TabLink>
        </nav>

        <div className="p-5 sm:p-7">
          {activeTab === 'overview' ? <Overview signal={signal} /> : null}
          {activeTab === 'related' ? <RelatedSignals signal={signal} related={related} returnTo={returnTo} initialInvestigation={initialInvestigation} /> : null}
          {activeTab === 'provenance' ? <Provenance signal={signal} audit={audit} /> : null}
        </div>
      </section>
    </main>
  )
}

function TabLink({
  signalId,
  returnTo,
  tab,
  active,
  children,
}: {
  signalId: string
  returnTo: string
  tab: DetailTab
  active: boolean
  children: React.ReactNode
}) {
  const params = new URLSearchParams({ tab, returnTo })
  return (
    <Link
      href={`/sinais/${signalId}?${params}`}
      aria-current={active ? 'page' : undefined}
      className={`flex min-h-12 shrink-0 items-center border-b-2 px-3 text-sm font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring ${
        active ? 'border-primary text-primary' : 'border-transparent text-muted-foreground hover:text-foreground'
      }`}
    >
      {children}
    </Link>
  )
}

function Overview({ signal }: { signal: IndividualSignalDetail }) {
  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_360px]">
      <div className="space-y-6">
        <section aria-labelledby="texto-fonte">
          <div className="flex items-center gap-2">
            <FileText className="size-5 text-primary" aria-hidden />
            <h2 id="texto-fonte" className="text-lg font-semibold">Texto original da fonte</h2>
          </div>
          <p className="mt-3 whitespace-pre-wrap text-sm leading-7 text-foreground">{signal.source.body}</p>
          {signal.source.url ? (
            <a
              href={signal.source.url}
              target="_blank"
              rel="noreferrer"
              className="mt-4 inline-flex min-h-11 items-center gap-2 rounded-md text-sm font-medium text-primary underline-offset-4 hover:underline"
            >
              Abrir publicação original <ExternalLink className="size-4" aria-hidden />
            </a>
          ) : null}
        </section>

        <section aria-labelledby="ficha-tecnica" className="border-t border-border pt-6">
          <h2 id="ficha-tecnica" className="text-lg font-semibold">Ficha técnica</h2>
          <p className="mt-1 text-sm text-muted-foreground">Campos extraídos para apoiar a leitura. Devem ser conferidos pelo analista.</p>
          {signal.technicalSheet ? (
            <dl className="mt-4 grid gap-3 sm:grid-cols-2">
              {Object.entries(signal.technicalSheet).map(([key, value]) => (
                <div key={key} className="rounded-lg border border-border bg-muted/25 p-4">
                  <dt className="text-xs font-medium text-muted-foreground">{fieldLabel(key)}</dt>
                  <dd className="mt-1 text-sm leading-relaxed text-foreground">{formatFieldValue(value)}</dd>
                </div>
              ))}
            </dl>
          ) : (
            <EmptyMessage title="Ficha técnica ainda indisponível" description="O texto original permanece disponível para investigação." />
          )}
        </section>
      </div>

      <aside className="space-y-4">
        <Card className="gap-0 p-5">
          <h2 className="text-sm font-semibold">Sobre este sinal</h2>
          <dl className="mt-4 space-y-4 text-sm">
            <MetaRow icon={signal.sourceKind === 'media' ? Newspaper : Radio} label="Tipo de fonte" value={SOURCE_LABEL[signal.sourceKind]} />
            <MetaRow icon={CalendarClock} label="Publicado em" value={formatDate(signal.publishedAt)} />
            <MetaRow icon={Clock3} label="Detectado em" value={formatDate(signal.createdAt)} />
            <MetaRow icon={Link2} label="Identificador externo" value={signal.source.externalId ?? 'Não informado'} />
          </dl>
        </Card>
        <div className="rounded-lg border border-andiroba/30 bg-andiroba/10 p-4 text-sm leading-relaxed text-foreground">
          <div className="flex items-center gap-2 font-medium"><ShieldCheck className="size-4 text-andiroba" aria-hidden /> Decisão humana</div>
          <p className="mt-2 text-muted-foreground">Este registro é um sinal para investigação, não a confirmação de evento ou caso clínico.</p>
        </div>
      </aside>
    </div>
  )
}

function RelatedSignals({
  signal,
  related,
  returnTo,
  initialInvestigation,
}: {
  signal: IndividualSignalDetail
  related: RelatedSignalPage
  returnTo: string
  initialInvestigation: InvestigationDetail | null
}) {
  return (
    <section aria-labelledby="relacionados-heading">
      <div className="max-w-3xl">
        <h2 id="relacionados-heading" className="text-lg font-semibold">Sinais relacionados</h2>
        <p className="mt-1 text-sm leading-relaxed text-muted-foreground">
          Sugestões da IA não associam sinais automaticamente. Compare as fontes e decida quais pertencem à mesma investigação.
        </p>
      </div>

      {related.items.length === 0 ? (
        <div className="mt-6"><EmptyMessage title="Nenhum sinal relacionado sugerido" description="O sinal principal pode continuar sendo investigado individualmente." /></div>
      ) : null}
      <div className="mt-6"><InvestigationComposer signal={signal} related={related} returnTo={returnTo} initialInvestigation={initialInvestigation} /></div>
    </section>
  )
}

function Provenance({ signal, audit }: { signal: IndividualSignalDetail; audit: SignalAuditEvent[] }) {
  return (
    <section aria-labelledby="proveniencia-heading" className="max-w-3xl">
      <h2 id="proveniencia-heading" className="text-lg font-semibold">Proveniência e rastreabilidade</h2>
      <p className="mt-1 text-sm text-muted-foreground">Informações técnicas que permitem rastrear como o sinal entrou no ambiente demonstrativo.</p>
      <dl className="mt-5 grid gap-3 sm:grid-cols-2">
        <Definition label="Adaptador" value={`${signal.provenance.adapterName} ${signal.provenance.adapterVersion}`} />
        <Definition label="Coletado em" value={formatDate(signal.provenance.collectedAt)} />
        <Definition label="Gerador" value={[signal.provenance.generatorName, signal.provenance.generatorVersion].filter(Boolean).join(' ') || 'Não informado'} />
        <Definition label="Cenário" value={signal.provenance.scenarioId ?? 'Não informado'} />
        <Definition label="Semente reproduzível" value={signal.provenance.seed?.toString() ?? 'Não informada'} />
        <Definition label="Contrato" value={signal.contractVersion} />
      </dl>
      <div className="mt-8 border-t border-border pt-6">
        <h3 className="font-semibold">Trilha de auditoria</h3>
        {audit.length === 0 ? (
          <p className="mt-2 text-sm text-muted-foreground">Nenhuma mudança humana foi registrada para este sinal.</p>
        ) : (
          <ol className="mt-4 space-y-3">
            {audit.map((event) => (
              <li key={event.id} className="rounded-lg border border-border p-4 text-sm">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <p className="font-medium">Estado atualizado para {STATE_LABEL[event.state]}</p>
                  <time className="text-xs text-muted-foreground" dateTime={event.occurredAt}>{formatDate(event.occurredAt)}</time>
                </div>
                <p className="mt-1 text-muted-foreground">Responsável: {event.actorId}{event.comment ? ` · ${event.comment}` : ''}</p>
              </li>
            ))}
          </ol>
        )}
      </div>
    </section>
  )
}

function Definition({ label, value }: { label: string; value: string }) {
  return <div className="rounded-lg border border-border p-4"><dt className="text-xs text-muted-foreground">{label}</dt><dd className="mt-1 break-words text-sm font-medium">{value}</dd></div>
}

function MetaRow({ icon: Icon, label, value }: { icon: typeof MapPin; label: string; value: string }) {
  return <div className="flex gap-3"><Icon className="mt-0.5 size-4 shrink-0 text-primary" aria-hidden /><div><dt className="text-xs text-muted-foreground">{label}</dt><dd className="mt-0.5 break-words font-medium">{value}</dd></div></div>
}

function EmptyMessage({ title, description }: { title: string; description: string }) {
  return <div className="rounded-lg border border-dashed border-border bg-muted/20 p-6 text-center"><p className="font-medium">{title}</p><p className="mt-1 text-sm text-muted-foreground">{description}</p></div>
}

function StateBadge({ state }: { state: IndividualSignalState }) {
  return <span className="inline-flex shrink-0 items-center rounded-full border border-primary-foreground/30 bg-primary-foreground/10 px-3 py-1.5 text-xs font-medium">{STATE_LABEL[state]}</span>
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat('pt-BR', { dateStyle: 'medium', timeStyle: 'short', timeZone: 'America/Manaus' }).format(new Date(value))
}

function fieldLabel(value: string): string {
  const labels: Record<string, string> = {
    disease_or_condition: 'Condição mencionada',
    syndrome: 'Síndrome',
    symptoms: 'Sintomas',
    location: 'Localização',
    temporal: 'Período',
    estimated_cases: 'Quantidade mencionada',
    missing_fields: 'Campos não encontrados',
  }
  return labels[value] ?? value.replaceAll('_', ' ')
}

function formatFieldValue(value: unknown): string {
  if (value === null || value === undefined || value === '') return 'Não informado'
  if (Array.isArray(value)) return value.length === 0 ? 'Não informado' : value.map(formatFieldValue).join(', ')
  if (typeof value === 'object') return Object.entries(value as Record<string, unknown>)
    .filter(([, item]) => item !== null && item !== undefined && item !== '')
    .map(([key, item]) => `${fieldLabel(key)}: ${formatFieldValue(item)}`)
    .join(' · ') || 'Não informado'
  if (typeof value === 'boolean') return value ? 'Sim' : 'Não'
  return String(value)
}

const SOURCE_LABEL: Record<'media' | 'community', string> = {
  media: 'Mídia',
  community: 'Relato comunitário',
}

const STATE_LABEL: Record<IndividualSignalState, string> = {
  detected: 'Detectado',
  triage: 'Em triagem',
  verification: 'Em verificação',
  risk_assessment: 'Em avaliação de risco',
  closed: 'Encerrado',
}
