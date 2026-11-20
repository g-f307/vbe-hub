'use client'

import Link from 'next/link'
import { useState } from 'react'
import {
  CalendarClock,
  CalendarRange,
  ChevronRight,
  ExternalLink,
  FileText,
  GitBranch,
  Layers3,
  Newspaper,
  Shield,
  Stethoscope,
  Tag,
  TriangleAlert,
  UsersRound,
  type LucideIcon,
} from 'lucide-react'

import type {
  IndividualSignalDetail,
  InvestigationDetail,
  RelatedSignalPage,
} from '@/lib/individual-signal-read'
import {
  selectableRelatedSignals,
  type InvestigationDetail as Composition,
} from '@/lib/investigation-client'
import {
  formatInformationDate,
  informationForSignal,
} from '@/lib/signal-information'
import {
  resolveSignalNavigation,
  resolveSignalTab,
  signalHref,
  type SignalTab,
} from '@/lib/signal-navigation'
import {
  InvestigationComposer,
  normalizeInvestigation,
} from '@/components/investigation-composer'
import { EvidenceTimeline } from '@/components/evidence-timeline'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogTrigger,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/v0/components/ui/dialog'

export function IndividualSignalDetailView({
  signal,
  related,
  returnTo,
  activeTab,
  initialInvestigation = null,
  openCandidates = false,
  relatedUnavailable = false,
}: {
  signal: IndividualSignalDetail
  related: RelatedSignalPage
  returnTo: string
  activeTab: SignalTab | 'related'
  initialInvestigation?: InvestigationDetail | null
  openCandidates?: boolean
  relatedUnavailable?: boolean
}) {
  const SourceIcon = signal.sourceKind === 'media' ? Newspaper : UsersRound
  const [investigation, setInvestigation] = useState(() =>
    normalizeInvestigation(initialInvestigation),
  )
  const [candidatesOpen, setCandidatesOpen] = useState(
    openCandidates || activeTab === 'related',
  )
  const [busy, setBusy] = useState(false)
  const [notice, setNotice] = useState<string | null>(null)
  const readOnly =
    investigation !== null && investigation.headSignalId !== signal.id
  const head = readOnly
    ? investigation.members.find(
        (member) => member.signal.id === investigation.headSignalId,
      )
    : null
  const navigation = resolveSignalNavigation(
    returnTo,
    readOnly ? investigation.headSignalId : null,
  )
  const tab = readOnly ? 'overview' : resolveSignalTab(activeTab).tab
  const evidence = readOnly
    ? []
    : (investigation?.members.filter(
        (member) => member.signal.id !== signal.id,
      ) ?? [])
  const candidates = selectableRelatedSignals(related.items).filter(
    (item) =>
      item.candidate.id !== signal.id &&
      !investigation?.members.some(
        (member) => member.signal.id === item.candidate.id,
      ),
  )

  function changed(value: Composition) {
    setInvestigation(value)
    setNotice('Sinais relacionados atualizados.')
    setCandidatesOpen(false)
    window.history.replaceState(
      null,
      '',
      signalHref(signal.id, 'evidence', returnTo),
    )
  }

  function toggleCandidates(open: boolean) {
    if (busy) return
    setCandidatesOpen(open)
    const href = signalHref(signal.id, 'evidence', returnTo)
    window.history.replaceState(
      null,
      '',
      open ? `${href}&candidates=open` : href,
    )
  }

  return (
    <main
      id="conteudo-principal"
      data-detail-layout="investigation-workspace"
      className="mx-auto w-full max-w-screen-2xl px-4 pb-8 sm:px-6 lg:px-8"
    >
      <div
        data-detail-chrome="header-and-tabs"
        className="relative rounded-b-2xl border-x border-b border-border bg-card shadow-sm"
      >
        <header
          data-detail-header="signal-record"
          className="px-5 pb-6 pt-5 sm:px-8"
        >
          <nav
            aria-label="Trilha de navegação"
            className="flex min-w-0 flex-wrap items-center gap-1.5 text-xs text-muted-foreground"
          >
            <Link
              href={navigation.queueHref}
              className="shrink-0 rounded font-medium hover:text-foreground focus-visible:outline-2 focus-visible:outline-ring"
            >
              Sinais detectados
            </Link>
            <ChevronRight className="size-3.5 shrink-0" aria-hidden />
            {head && navigation.headHref ? (
              <>
                <Link
                  href={navigation.headHref}
                  className="max-w-full truncate font-medium text-primary"
                >
                  {head.signal.title}
                </Link>
                <ChevronRight className="size-3.5 shrink-0" aria-hidden />
              </>
            ) : null}
            <span
              aria-current="page"
              className="min-w-0 truncate font-medium text-foreground"
            >
              {signal.title}
            </span>
          </nav>
          <div className="mt-5 flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
            <div className="flex min-w-0 items-start gap-4">
              <span className="inline-flex size-12 shrink-0 items-center justify-center rounded-xl border border-border bg-muted/40 text-primary">
                <SourceIcon className="size-5" aria-hidden />
              </span>
              <div className="min-w-0">
                <h1 className="text-balance text-2xl font-semibold leading-tight tracking-tight text-foreground sm:text-[26px]">
                  {signal.title}
                </h1>
                <p className="mt-2 flex items-center gap-2 text-sm text-muted-foreground">
                  <SourceIcon className="size-4" aria-hidden />
                  {signal.sourceName.startsWith('demo-')
                    ? signal.sourceKind === 'media'
                      ? 'Mídia'
                      : 'Relato comunitário'
                    : signal.sourceName}
                </p>
              </div>
            </div>
          </div>
        </header>
        <div
          data-workspace-tabs="true"
          className="absolute left-1/2 top-full w-fit max-w-[calc(100%-2rem)] -translate-x-1/2 rounded-xl border border-border bg-muted/95 p-1.5 shadow-sm"
        >
          <nav
            aria-label="Seções do sinal"
            className="flex w-max max-w-full gap-1 overflow-x-auto"
          >
            <TabLink
              href={signalHref(signal.id, 'overview', returnTo)}
              active={tab === 'overview'}
              icon={FileText}
            >
              Informações
            </TabLink>
            {!readOnly ? (
              <TabLink
                href={signalHref(signal.id, 'evidence', returnTo)}
                active={tab === 'evidence'}
                icon={Layers3}
              >
                Sinais relacionados{' '}
                <span className="ml-1 text-xs">{evidence.length}</span>
              </TabLink>
            ) : null}
          </nav>
        </div>
      </div>
      <div className="mt-16 rounded-2xl bg-muted/45 p-3 sm:p-4">
        {notice ? (
          <p role="status" className="mb-3 text-sm text-primary">
            {notice}
          </p>
        ) : null}
        {tab === 'overview' ? (
          <Overview
            signal={signal}
            investigation={readOnly ? null : investigation}
            returnTo={navigation.queueHref}
          />
        ) : (
          <Panel
            id="sinais-relacionados"
            title="Sinais relacionados"
            description="Consulte os sinais incorporados ou procure novas relações para esta investigação."
          >
            <div className="mb-5 flex flex-wrap items-center justify-end gap-3">
              <Dialog open={candidatesOpen} onOpenChange={toggleCandidates}>
                <DialogTrigger asChild>
                  <Button type="button" disabled={relatedUnavailable}>
                    <GitBranch aria-hidden />
                    Possíveis sinais relacionados{' '}
                    <span
                      aria-label={`${candidates.length} disponíveis`}
                      className="ml-1 rounded-full bg-white/20 px-2 py-0.5 text-xs tabular-nums"
                    >
                      {candidates.length}
                    </span>
                  </Button>
                </DialogTrigger>
                <DialogContent
                  className="flex max-h-[90dvh] flex-col gap-0 overflow-hidden p-0 sm:max-w-5xl"
                  showCloseButton={!busy}
                  onEscapeKeyDown={(event) => {
                    if (busy) event.preventDefault()
                  }}
                  onPointerDownOutside={(event) => {
                    if (busy) event.preventDefault()
                  }}
                >
                  <DialogHeader className="shrink-0 border-b border-border px-5 py-5 pr-12 text-left sm:px-6">
                    <DialogTitle>Possíveis sinais relacionados</DialogTitle>
                    <DialogDescription>
                      Sugestões da IA não associam sinais automaticamente.
                      Selecione os sinais que deseja incorporar a “
                      {signal.title}”.
                    </DialogDescription>
                  </DialogHeader>
                  <div className="min-h-0 overflow-y-auto px-5 py-5 sm:px-6">
                    <InvestigationComposer
                      signal={signal}
                      related={related}
                      returnTo={returnTo}
                      initialInvestigation={investigation}
                      onChange={changed}
                      onBusy={setBusy}
                    />
                  </div>
                </DialogContent>
              </Dialog>
            </div>
            {relatedUnavailable ? (
              <p role="alert" className="mb-4 text-sm text-destructive">
                Não foi possível carregar as sugestões.{' '}
                <a
                  href={signalHref(signal.id, 'evidence', returnTo)}
                  className="underline"
                >
                  Tentar novamente
                </a>
              </p>
            ) : null}
            <InvestigationComposer
              signal={signal}
              related={related}
              returnTo={returnTo}
              initialInvestigation={investigation}
              mode="evidence"
              onChange={changed}
            />
          </Panel>
        )}
      </div>
    </main>
  )
}

function TabLink({
  href,
  active,
  icon: Icon,
  children,
}: {
  href: string
  active: boolean
  icon: LucideIcon
  children: React.ReactNode
}) {
  return (
    <Link
      href={href}
      aria-current={active ? 'page' : undefined}
      className={`flex min-h-10 shrink-0 items-center gap-2 rounded-lg px-3.5 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${active ? 'bg-card text-primary shadow-sm ring-1 ring-border' : 'text-muted-foreground hover:bg-card/70 hover:text-foreground'}`}
    >
      <Icon className="size-4" aria-hidden />
      {children}
    </Link>
  )
}

function Panel({
  id,
  title,
  description,
  children,
}: {
  id: string
  title: string
  description?: string
  children: React.ReactNode
}) {
  return (
    <section
      data-panel-tone="card"
      aria-labelledby={id}
      className="h-full rounded-2xl border border-border bg-card px-5 py-5 shadow-sm sm:px-6"
    >
      <h2 id={id} className="text-sm font-semibold text-foreground">
        {title}
      </h2>
      {description ? (
        <p className="mt-0.5 text-xs text-muted-foreground">{description}</p>
      ) : null}
      <div className="mt-4">{children}</div>
    </section>
  )
}

function Overview({
  signal,
  investigation,
  returnTo,
}: {
  signal: IndividualSignalDetail
  investigation: Composition | null
  returnTo: string
}) {
  const info = investigation?.information ?? informationForSignal(signal)
  const evidence =
    investigation?.members.filter(
      (member) => member.signal.id !== investigation.headSignalId,
    ) ?? []
  const fields: Array<{
    key: string
    label: string
    value: React.ReactNode
    icon: LucideIcon
  }> = [
    {
      key: 'confidentiality',
      label: 'Confidencialidade',
      value: info.confidentiality,
      icon: Shield,
    },
    {
      key: 'signal_type',
      label: 'Tipo de sinal',
      value: info.signal_type,
      icon: FileText,
    },
    {
      key: 'etiology',
      label: 'Etiologia',
      value: info.etiology,
      icon: Stethoscope,
    },
    {
      key: 'hazard_general',
      label: 'Perigo geral',
      value: info.hazard_general,
      icon: TriangleAlert,
    },
    {
      key: 'hazard_specific',
      label: 'Perigo específico',
      value: info.hazard_specific,
      icon: TriangleAlert,
    },
    {
      key: 'tags',
      label: 'Etiquetas',
      value: info.tags.length ? (
        <span className="flex flex-wrap gap-x-2 gap-y-1">
          {info.tags.map((tag) => (
            <span key={tag}>{tag}</span>
          ))}
        </span>
      ) : null,
      icon: Tag,
    },
    {
      key: 'signal_date',
      label: 'Data do sinal',
      value: formatInformationDate(info.signal_date),
      icon: CalendarRange,
    },
    {
      key: 'detected_at',
      label: 'Data de detecção',
      value: formatInformationDate(info.detected_at),
      icon: CalendarClock,
    },
    {
      key: 'notified_at',
      label: 'Data de notificação',
      value: formatInformationDate(info.notified_at),
      icon: CalendarClock,
    },
  ]
  return (
    <div
      data-overview-layout="reading-and-context"
      className="grid items-stretch gap-4 lg:grid-cols-12"
    >
      <div className="min-w-0 lg:col-span-8">
        <Panel id="ficha-tecnica" title="Ficha técnica">
          <dl className="grid gap-3 sm:grid-cols-2">
            {fields.map(({ key, label, value, icon: Icon }) => (
              <div
                key={key}
                data-information-field={key}
                className="flex items-center gap-3 rounded-xl border border-border p-3"
              >
                <Icon className="size-4 shrink-0 text-primary" aria-hidden />
                <div className="min-w-0">
                  <dt className="text-sm font-medium text-foreground">
                    {label}
                  </dt>
                  <dd className="mt-0.5 break-words text-xs leading-relaxed text-muted-foreground">
                    {value || 'Não informado'}
                  </dd>
                </div>
              </div>
            ))}
          </dl>
        </Panel>
      </div>
      <aside
        data-text-position="side"
        className={`${evidence.length ? 'grid min-h-0 grid-rows-2 gap-4' : ''} lg:col-span-4`}
      >
        <div
          className={
            evidence.length ? 'min-h-0 overflow-y-auto rounded-2xl' : 'h-full'
          }
        >
          <Panel id="descricao" title="Descrição">
            <div className="border-t border-border pt-4">
              <p className="whitespace-pre-wrap break-words text-sm leading-6 text-foreground">
                {signal.source.body}
              </p>
              {signal.source.url ? (
                <a
                  href={signal.source.url}
                  target="_blank"
                  rel="noreferrer"
                  className="mt-4 inline-flex min-h-10 items-center gap-2 text-sm font-medium text-primary hover:underline"
                >
                  Abrir publicação original{' '}
                  <ExternalLink className="size-4" aria-hidden />
                </a>
              ) : null}
            </div>
          </Panel>
        </div>
        {evidence.length && investigation ? (
          <div className="min-h-0 overflow-y-auto rounded-2xl">
            <Panel id="evidencias-incorporadas" title="Evidências incorporadas">
              <EvidenceTimeline
                items={evidence}
                headSignalId={investigation.headSignalId}
                returnTo={returnTo}
                originTab="overview"
                compact
              />
            </Panel>
          </div>
        ) : null}
      </aside>
    </div>
  )
}
