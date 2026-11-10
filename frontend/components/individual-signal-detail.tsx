import Link from 'next/link'
import {
  Activity,
  CalendarClock,
  CalendarRange,
  ChevronRight,
  ClipboardList,
  Clock3,
  ExternalLink,
  FileText,
  GitBranch,
  Layers3,
  Info,
  MapPin,
  Newspaper,
  Stethoscope,
  Thermometer,
  UsersRound,
  type LucideIcon,
} from 'lucide-react'

import type {
  IndividualSignalDetail,
  IndividualSignalState,
  InvestigationDetail,
  RelatedSignalPage,
} from '@/lib/individual-signal-read'
import { InvestigationComposer } from '@/components/investigation-composer'

type DetailTab = 'overview' | 'related' | 'evidence'

export function IndividualSignalDetailView({
  signal,
  related,
  returnTo,
  activeTab,
  initialInvestigation = null,
}: {
  signal: IndividualSignalDetail
  related: RelatedSignalPage
  returnTo: string
  activeTab: DetailTab
  initialInvestigation?: InvestigationDetail | null
}) {
  const SourceIcon = signal.sourceKind === 'media' ? Newspaper : UsersRound
  return (
    <main id="conteudo-principal" data-detail-layout="investigation-workspace" className="mx-auto w-full max-w-screen-2xl px-4 pb-8 sm:px-6 lg:px-8">
      <div data-detail-chrome="header-and-tabs" className="relative rounded-b-2xl border-x border-b border-border bg-card shadow-sm">
        <header data-detail-header="signal-record" className="px-5 pb-6 pt-5 sm:px-8">
          <nav aria-label="Trilha de navegação" className="flex min-w-0 items-center gap-1.5 text-xs text-muted-foreground">
            <Link href={returnTo} className="shrink-0 rounded font-medium hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
              Sinais detectados
            </Link>
            <ChevronRight className="size-3.5 shrink-0" aria-hidden />
            <span className="truncate font-medium text-foreground">{signal.title}</span>
          </nav>

          <div className="mt-5 flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
            <div className="flex min-w-0 items-start gap-4">
              <span className="inline-flex size-12 shrink-0 items-center justify-center rounded-xl border border-border bg-muted/40 text-primary">
                <SourceIcon className="size-5" aria-hidden />
              </span>
              <div className="min-w-0">
                <h1 className="text-balance text-2xl font-semibold leading-tight tracking-tight text-foreground sm:text-[26px]">{signal.title}</h1>
                <dl data-signal-facts="true" className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-muted-foreground">
                  <InlineFact icon={SourceIcon} label="Fonte" value={displaySourceName(signal)} />
                  <InlineFact icon={CalendarClock} label="Publicado em" value={formatDate(signal.publishedAt)} />
                </dl>
              </div>
            </div>

            <div className="flex shrink-0 flex-col gap-3 lg:items-end">
              <p className="flex items-baseline gap-2 text-sm text-muted-foreground">
                <Clock3 className="size-4 self-center" aria-hidden />
                Detectado em <span className="text-base font-semibold text-foreground">{formatDate(signal.createdAt)}</span>
              </p>
            </div>
          </div>
        </header>

        <div data-workspace-tabs="true" className="absolute left-1/2 top-full w-fit max-w-[calc(100%-2rem)] -translate-x-1/2 rounded-xl border border-border bg-muted/95 p-1.5 shadow-sm">
            <nav aria-label="Seções do sinal" className="flex w-max max-w-full gap-1 overflow-x-auto">
              <TabLink signalId={signal.id} returnTo={returnTo} tab="overview" active={activeTab === 'overview'} icon={FileText}>
                Analisar sinal
              </TabLink>
              <TabLink signalId={signal.id} returnTo={returnTo} tab="related" active={activeTab === 'related'} icon={GitBranch}>
                Relacionar sinais
                <span className="ml-1.5 text-xs opacity-70">{related.items.length}</span>
              </TabLink>
              <TabLink signalId={signal.id} returnTo={returnTo} tab="evidence" active={activeTab === 'evidence'} icon={Layers3}>
                Gerenciar evidências
                <span className="ml-1.5 text-xs opacity-70">{evidenceMembers(initialInvestigation).length}</span>
              </TabLink>
            </nav>
        </div>
      </div>

            <div className="mt-16 rounded-2xl bg-muted/45 p-3 sm:p-4">
              {activeTab === 'overview' ? <Overview signal={signal} investigation={initialInvestigation} /> : null}
              {activeTab === 'related' ? <RelatedSignals signal={signal} related={related} returnTo={returnTo} initialInvestigation={initialInvestigation} /> : null}
              {activeTab === 'evidence' ? <EvidenceManager signal={signal} related={related} returnTo={returnTo} investigation={initialInvestigation} /> : null}
            </div>
    </main>
  )
}

function tabHref(signalId: string, tab: DetailTab, returnTo: string): string {
  return `/sinais/${signalId}?${new URLSearchParams({ tab, returnTo })}`
}

function TabLink({
  signalId,
  returnTo,
  tab,
  active,
  icon: Icon,
  children,
}: {
  signalId: string
  returnTo: string
  tab: DetailTab
  active: boolean
  icon: LucideIcon
  children: React.ReactNode
}) {
  return (
    <Link
      href={tabHref(signalId, tab, returnTo)}
      aria-current={active ? 'page' : undefined}
      className={`flex min-h-10 shrink-0 items-center gap-2 rounded-lg px-3.5 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${
        active ? 'bg-card text-primary shadow-sm ring-1 ring-border' : 'text-muted-foreground hover:bg-card/70 hover:text-foreground'
      }`}
    >
      <Icon className="size-4" aria-hidden />
      {children}
    </Link>
  )
}

function Panel({ id, title, description, children }: { id: string; title: string; description?: string; children: React.ReactNode }) {
  return (
    <section data-panel-tone="card" aria-labelledby={id} className="h-full rounded-2xl border border-border bg-card px-5 py-5 shadow-sm sm:px-6">
      <h2 id={id} className="scroll-mt-20 text-sm font-semibold text-foreground">{title}</h2>
      {description ? <p className="mt-0.5 text-xs text-muted-foreground">{description}</p> : null}
      <div className="mt-4">{children}</div>
    </section>
  )
}

function Overview({ signal, investigation }: { signal: IndividualSignalDetail; investigation: InvestigationDetail | null }) {
  const projectedSheet = investigation?.technicalSheet ?? signal.technicalSheet
  const technicalFields = projectedSheet
    ? Object.entries(projectedSheet).filter(([key]) => !HIDDEN_TECHNICAL_FIELDS.has(key))
    : []
  return (
    <div data-overview-layout="reading-and-context" data-overview-dashboard="true" className="grid items-stretch gap-4 lg:grid-cols-12">
      <div className={`min-w-0 ${investigation ? 'lg:col-span-12' : 'lg:col-span-8'}`}>
        <Panel id="ficha-tecnica" title="Ficha técnica" description="Leitura estruturada extraída do conteúdo. Confira cada campo antes de usá-lo na investigação.">
          <dl className="grid gap-3 sm:grid-cols-2">
            <ItemCard icon={Activity} label="Etapa" value={STATE_LABEL[signal.state]} state={signal.state} />
            {technicalFields.map(([key, value]) => (
              <ItemCard key={key} icon={FIELD_ICON[key] ?? ClipboardList} label={fieldLabel(key)} value={formatFieldValue(value)} />
            ))}
          </dl>
          {technicalFields.length === 0 ? (
            <p className="mt-3 text-center text-xs text-muted-foreground">Os demais campos da ficha técnica ainda não estão disponíveis.</p>
          ) : null}
        </Panel>
      </div>

      <aside data-text-position="side" className={investigation ? 'lg:col-span-6' : 'lg:col-span-4'}>
        <Panel id="texto-fonte" title="Texto original da fonte" description="Conteúdo preservado para leitura e comparação pelo analista.">
          <div className="border-t border-border pt-4">
            <p className="whitespace-pre-wrap break-words text-sm leading-6 text-foreground">{signal.source.body}</p>
            {signal.source.url ? (
              <a
                href={signal.source.url}
                target="_blank"
                rel="noreferrer"
                className="mt-4 inline-flex min-h-10 items-center gap-2 border-t border-border pt-3 text-sm font-medium text-primary underline-offset-4 hover:underline"
              >
                Abrir publicação original <ExternalLink className="size-4" aria-hidden />
              </a>
            ) : null}
          </div>
        </Panel>
      </aside>

      {investigation ? (
        <aside className="lg:col-span-6">
          <Panel id="evidencias-incorporadas" title="Evidências incorporadas" description="Sinais relacionados preservados como fontes independentes desta investigação.">
            <EvidenceCards investigation={investigation} compact />
          </Panel>
        </aside>
      ) : null}

      {!investigation ? <div data-context-position="full" className="lg:col-span-12">
        <section aria-labelledby="contexto-analise" className="h-full rounded-2xl border border-border bg-card p-5 shadow-sm sm:p-6">
          <h2 id="contexto-analise" className="text-sm font-semibold">Contexto da análise</h2>
          <p className="mt-1 text-sm leading-6 text-muted-foreground">Este é um registro individual. Outros sinais permanecem separados até a decisão explícita do analista.</p>
        </section>
      </div> : null}
    </div>
  )
}

function EvidenceManager({
  signal,
  related,
  returnTo,
  investigation,
}: {
  signal: IndividualSignalDetail
  related: RelatedSignalPage
  returnTo: string
  investigation: InvestigationDetail | null
}) {
  return (
    <Panel id="gerenciar-evidencias" title="Gerenciar evidências" description="Consulte ou desfaça vínculos. Nenhum conteúdo original é alterado ou apagado.">
      <InvestigationComposer signal={signal} related={related} returnTo={returnTo} initialInvestigation={investigation} mode="evidence" />
    </Panel>
  )
}

function EvidenceCards({ investigation, compact = false }: { investigation: InvestigationDetail; compact?: boolean }) {
  const members = evidenceMembers(investigation)
  if (members.length === 0) return <EmptyMessage title="Nenhuma evidência incorporada" description="Os sinais confirmados pelo analista aparecerão aqui sem perder seu texto original." />
  return (
    <div className="grid gap-3">
      {members.map((member) => (
        <article key={member.signal.id} className="rounded-xl border border-border bg-background p-4">
          <p className="text-xs text-muted-foreground">{displaySourceName(member.signal)} · {formatDate(member.signal.publishedAt)}</p>
          <h3 className="mt-1 text-sm font-semibold">{member.signal.title}</h3>
          <p className={`${compact ? 'line-clamp-4' : ''} mt-2 whitespace-pre-wrap text-sm leading-6 text-muted-foreground`}>{member.signal.source.body}</p>
        </article>
      ))}
    </div>
  )
}

function evidenceMembers(investigation: InvestigationDetail | null) {
  return investigation?.members.filter((member) => member.signal.id !== investigation.headSignalId) ?? []
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
    <Panel
      id="relacionados-heading"
      title="Sinais relacionados"
      description="Sugestões da IA não associam sinais automaticamente. Compare as fontes e decida quais pertencem à mesma investigação."
    >
      {related.items.length === 0 ? (
        <div className="mb-5"><EmptyMessage title="Nenhum sinal relacionado sugerido" description="O sinal principal pode continuar sendo investigado individualmente." /></div>
      ) : null}
      <InvestigationComposer signal={signal} related={related} returnTo={returnTo} initialInvestigation={initialInvestigation} />
    </Panel>
  )
}

function ItemCard({ icon: Icon, label, value, state }: { icon: LucideIcon; label: string; value: string; state?: IndividualSignalState }) {
  return (
    <div data-technical-item="true" data-technical-state={state} className="flex items-center gap-3 rounded-xl border border-border p-3">
      <Icon className="size-4 shrink-0 text-primary" aria-hidden />
      <div className="min-w-0">
        <dt className="text-sm font-medium text-foreground">{label}</dt>
        <dd className="mt-0.5 break-words text-xs leading-relaxed text-muted-foreground">{value}</dd>
      </div>
    </div>
  )
}

function InlineFact({ icon: Icon, label, value }: { icon: LucideIcon; label: string; value: string }) {
  return (
    <div className="flex min-w-0 items-center gap-1.5">
      <Icon className="size-3.5 shrink-0" aria-hidden />
      <dt className="sr-only">{label}</dt>
      <dd className="break-words">{value}</dd>
    </div>
  )
}

function EmptyMessage({ title, description }: { title: string; description: string }) {
  return <div className="rounded-xl border border-dashed border-border bg-muted/20 p-6 text-center"><p className="text-sm font-medium">{title}</p><p className="mt-1 text-xs text-muted-foreground">{description}</p></div>
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat('pt-BR', { dateStyle: 'medium', timeStyle: 'short', timeZone: 'America/Manaus' }).format(new Date(value))
}

function displaySourceName(signal: IndividualSignalDetail): string {
  return signal.sourceName.startsWith('demo-') ? SOURCE_LABEL[signal.sourceKind] : signal.sourceName
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
    municipality: 'Município',
    district: 'Bairro',
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

const FIELD_ICON: Record<string, LucideIcon> = {
  disease_or_condition: Stethoscope,
  syndrome: Activity,
  symptoms: Thermometer,
  location: MapPin,
  temporal: CalendarRange,
  estimated_cases: UsersRound,
  missing_fields: Info,
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

const HIDDEN_TECHNICAL_FIELDS = new Set([
  'evidence',
  'confidence',
  'record_nature',
  'action_in_progress',
  'suggested_relevance',
])
