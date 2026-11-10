import Link from 'next/link'
import { CalendarClock, ChevronRight, Filter, Inbox, Newspaper, Search, UsersRound } from 'lucide-react'

import type {
  IndividualSignalCard,
  IndividualSignalState,
  IndividualSourceKind,
} from '@/lib/individual-signal-read'
import { ViewSelector, type DetectedView } from '@/components/view-selector'

export type DetectedFilters = {
  state?: IndividualSignalState | 'all'
  sourceKind?: IndividualSourceKind | 'all'
  query?: string
  cursor?: string
  view?: DetectedView
}

export function DetectedSignalsView({
  items,
  nextCursor,
  filters,
}: {
  items: IndividualSignalCard[]
  nextCursor: string | null
  filters: DetectedFilters
}) {
  const returnTo = buildQueueHref(filters)
  const view = filters.view ?? 'cards'
  const normalizedQuery = filters.query?.trim().toLocaleLowerCase('pt-BR') ?? ''
  const visibleItems = normalizedQuery
    ? items.filter((signal) => [signal.title, signal.excerpt, signal.sourceName].some((value) => value.toLocaleLowerCase('pt-BR').includes(normalizedQuery)))
    : items
  return (
    <main id="conteudo-principal" className="mx-auto w-full max-w-screen-2xl px-4 py-6 sm:px-6 lg:px-8">
      <div className="border-b border-border pb-5">
        <div>
          <h1 className="text-[26px] font-semibold tracking-tight text-foreground">Sinais detectados</h1>
          <p className="mt-2 max-w-3xl text-[13px] leading-relaxed text-muted-foreground">
            Cada card corresponde a uma única notícia ou relato comunitário. Abra o sinal para conferir a fonte e as sugestões relacionadas.
          </p>
        </div>
      </div>

      <div className="mt-5 flex flex-col gap-3 lg:flex-row lg:items-stretch">
      <form action="/" method="get" className="grid flex-1 gap-2 rounded-xl border border-border bg-card p-3 shadow-sm sm:grid-cols-2 lg:grid-cols-[minmax(200px,1fr)_170px_170px_auto]">
        <input type="hidden" name="view" value={view} />
        <label className="relative block">
          <span className="sr-only">Buscar nesta página</span>
          <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" aria-hidden />
          <input
            name="query"
            defaultValue={filters.query ?? ''}
            placeholder="Buscar no lote carregado"
            className="h-11 w-full rounded-md border border-input bg-background pl-10 pr-3 text-[13px] outline-none focus-visible:ring-2 focus-visible:ring-ring"
          />
        </label>
        <label>
          <span className="sr-only">Estado do fluxo</span>
          <select name="state" defaultValue={filters.state ?? 'detected'} className="h-11 w-full rounded-md border border-input bg-background px-3 text-[13px] outline-none focus-visible:ring-2 focus-visible:ring-ring">
            <option value="all">Todos os estados</option>
            <option value="detected">Detectados</option>
            <option value="triage">Em triagem</option>
            <option value="verification">Em verificação</option>
            <option value="risk_assessment">Avaliação de risco</option>
            <option value="closed">Encerrados</option>
          </select>
        </label>
        <label>
          <span className="sr-only">Tipo de fonte</span>
          <select name="source_kind" defaultValue={filters.sourceKind ?? 'all'} className="h-11 w-full rounded-md border border-input bg-background px-3 text-[13px] outline-none focus-visible:ring-2 focus-visible:ring-ring">
            <option value="all">Todas as fontes</option>
            <option value="media">Mídia</option>
            <option value="community">Relato comunitário</option>
          </select>
        </label>
        <button type="submit" className="inline-flex min-h-11 items-center justify-center gap-2 rounded-md bg-primary px-4 text-[13px] font-medium text-primary-foreground hover:bg-[var(--brand-primary-hover)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2">
          <Filter className="size-4" aria-hidden /> Aplicar
        </button>
      </form>
      <ViewSelector view={view} hrefs={{
        cards: buildQueueHref({ ...filters, cursor: undefined, view: 'cards' }),
        list: buildQueueHref({ ...filters, cursor: undefined, view: 'list' }),
        kanban: buildQueueHref({ ...filters, cursor: undefined, view: 'kanban' }),
      }} />
      </div>

      {filters.query ? (
        <p className="mt-3 text-xs text-muted-foreground">A busca textual filtra o lote atual. Os filtros de estado e fonte são aplicados em toda a coleção.</p>
      ) : null}

      {visibleItems.length === 0 ? (
        <div className="mt-6 rounded-xl border border-dashed border-border bg-muted/20 px-6 py-14 text-center">
          <Inbox className="mx-auto size-8 text-muted-foreground" aria-hidden />
          <h2 className="mt-3 font-semibold">Nenhum sinal encontrado</h2>
          <p className="mt-1 text-sm text-muted-foreground">Ajuste os filtros ou aguarde a entrada de novas fontes.</p>
          <Link href="/" className="mt-4 inline-flex min-h-11 items-center text-sm font-medium text-primary hover:underline">Limpar filtros</Link>
        </div>
      ) : view === 'list' ? (
        <SignalList items={visibleItems} returnTo={returnTo} />
      ) : view === 'kanban' ? (
        <SignalKanban items={visibleItems} returnTo={returnTo} />
      ) : (
        <section aria-label="Lista de sinais" className="mx-auto mt-6 grid w-full max-w-[1280px] justify-items-center gap-x-8 gap-y-6 md:grid-cols-2 xl:grid-cols-3">
          {visibleItems.map((signal) => <DetectedCard key={signal.id} signal={signal} returnTo={returnTo} />)}
        </section>
      )}

      <nav aria-label="Paginação dos sinais" className="mt-7 flex items-center justify-between border-t border-border pt-5">
        <p className="text-xs text-muted-foreground">Ordenação: detecção mais recente primeiro</p>
        {nextCursor ? (
          <Link href={buildQueueHref({ ...filters, cursor: nextCursor })} className="inline-flex min-h-11 items-center gap-2 rounded-md border border-border bg-card px-4 text-sm font-medium hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
            Próxima página <ChevronRight className="size-4" aria-hidden />
          </Link>
        ) : (
          <span className="text-sm text-muted-foreground">Fim da lista</span>
        )}
      </nav>
    </main>
  )
}

function SignalList({ items, returnTo }: { items: IndividualSignalCard[]; returnTo: string }) {
  return (
    <section aria-label="Sinais em lista" className="mt-6 overflow-hidden rounded-xl border border-border bg-card shadow-sm">
      <div className="hidden grid-cols-[minmax(280px,2fr)_165px_175px_145px_44px] items-center gap-3 bg-muted/55 px-4 py-3 text-[11px] font-semibold tracking-wide text-muted-foreground uppercase md:grid">
        <span>Sinal</span>
        <span>Fonte</span>
        <span>Publicação</span>
        <span>Etapa</span>
        <span className="sr-only">Ação</span>
      </div>
      <ul>
        {items.map((signal) => {
          const Icon = signal.sourceKind === 'media' ? Newspaper : UsersRound
          return (
            <li key={signal.id} data-state-row={signal.state} className="relative border-t border-border">
              <span data-state-marker={signal.state} aria-hidden className={`absolute top-3 bottom-3 left-1 w-1 rounded-full ${STATE_VISUAL_STYLE[signal.state].rowMarker}`} />
              <Link href={signalHref(signal.id, returnTo)} className="group grid gap-3 py-4 pr-4 pl-5 transition-colors hover:bg-muted/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring md:grid-cols-[minmax(280px,2fr)_165px_175px_145px_44px] md:items-center md:gap-3">
                <span className="min-w-0">
                  <span className="block text-sm font-medium text-foreground">{signal.title}</span>
                  <span className="mt-1 block truncate text-[13px] text-muted-foreground">{signal.excerpt}</span>
                </span>
                <span data-source-label={signal.sourceKind} className="inline-flex w-fit items-center gap-1.5 text-xs font-medium text-foreground"><Icon className="size-4 text-muted-foreground" aria-hidden />{SOURCE_LABEL[signal.sourceKind]}</span>
                <span className="text-xs text-muted-foreground"><span className="mr-1 md:hidden">Publicação:</span>{formatDate(signal.publishedAt)}</span>
                <span className="text-xs font-medium text-foreground"><span className="mr-1 text-muted-foreground md:hidden">Etapa:</span>{STATE_LABEL[signal.state]}</span>
                <span className="hidden size-9 items-center justify-center justify-self-end rounded-md text-primary transition-colors group-hover:bg-primary/10 md:flex"><ChevronRight className="size-4" aria-hidden /><span className="sr-only">Abrir sinal</span></span>
              </Link>
            </li>
          )
        })}
      </ul>
    </section>
  )
}

function SignalKanban({ items, returnTo }: { items: IndividualSignalCard[]; returnTo: string }) {
  return (
    <section aria-label="Quadro Kanban dos sinais" className="mt-6 flex gap-4 overflow-x-auto px-1 pb-4">
      {STATE_ORDER.map((state) => {
        const signals = items.filter((signal) => signal.state === state)
        return (
          <div key={state} className="flex min-w-[280px] flex-1 flex-col">
            <div className="mb-3">
              <div className={`mb-3 h-1.5 rounded-full ${STATE_VISUAL_STYLE[state].line}`} />
              <div className="flex items-center justify-between gap-3">
                <h2 className="text-sm font-semibold text-foreground">{STATE_LABEL[state]}</h2>
                <span className="rounded-full bg-muted px-2 py-1 text-xs font-medium text-muted-foreground">{signals.length}</span>
              </div>
            </div>
            <div className={`kanban-column flex flex-1 flex-col gap-3 rounded-lg p-3 ${STATE_VISUAL_STYLE[state].surface}`}>
              {signals.length === 0 ? <p className="flex h-24 items-center justify-center text-[13px] text-muted-foreground">Nenhum sinal</p> : signals.map((signal) => (
                <KanbanSignalCard key={signal.id} signal={signal} returnTo={returnTo} />
              ))}
            </div>
          </div>
        )
      })}
    </section>
  )
}

function KanbanSignalCard({ signal, returnTo }: { signal: IndividualSignalCard; returnTo: string }) {
  return (
    <Link
      href={signalHref(signal.id, returnTo)}
      aria-label={`Abrir sinal ${signal.title}`}
      className="relative flex min-h-[190px] w-full flex-col overflow-hidden rounded-lg border border-border bg-card shadow-sm hover:border-primary/40 hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
    >
      <span
        data-kanban-state-stripe={signal.state}
        aria-hidden
        className={`h-1.5 w-full shrink-0 ${STATE_VISUAL_STYLE[signal.state].line}`}
      />
      <div className="flex flex-1 flex-col p-4">
        <h3 className="text-[13px] font-medium leading-snug text-card-foreground">{signal.title}</h3>
        <p className="mt-2 line-clamp-2 text-xs leading-relaxed text-muted-foreground">{signal.excerpt}</p>
        <div className="mt-auto border-t border-border pt-3 text-[11px] text-muted-foreground">
          <p className="font-medium text-foreground">{SOURCE_LABEL[signal.sourceKind]}</p>
          <p className="mt-1 flex items-center gap-1.5"><CalendarClock className="size-3" aria-hidden />{formatDate(signal.publishedAt)}</p>
        </div>
      </div>
    </Link>
  )
}

function DetectedCard({ signal, returnTo }: { signal: IndividualSignalCard; returnTo: string }) {
  const params = new URLSearchParams({ returnTo })
  return (
    <Link
      href={`/sinais/${signal.id}?${params}`}
      aria-label={`Abrir sinal ${signal.title}`}
      data-layered-card="true"
      className={`group relative isolate flex min-h-[285px] w-full max-w-[385px] flex-col overflow-hidden rounded-xl shadow-sm transition-[box-shadow,transform] hover:-translate-y-0.5 hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 ${STATE_VISUAL_STYLE[signal.state].folder}`}
    >
      <span
        data-state-banner={signal.state}
        className={`relative z-0 flex min-h-10 items-start justify-center rounded-t-xl border border-b-0 border-white/25 px-4 pt-1.5 text-[11px] font-semibold tracking-wide text-white uppercase ${STATE_VISUAL_STYLE[signal.state].banner}`}
      >
        {STATE_LABEL[signal.state]}
      </span>
      <span aria-hidden className="absolute inset-x-2 top-8 bottom-1 z-0 rounded-xl border border-border/80 bg-card/75 shadow-sm" />
      <span data-progress-outline="true" aria-hidden className={`pointer-events-none absolute inset-0 z-30 rounded-xl border-[4px] [clip-path:inset(0_0_50%_0)] transition-[clip-path,box-shadow] duration-300 group-hover:[clip-path:inset(0_0_0_0)] group-hover:shadow-[0_0_18px_rgba(63,100,130,0.28)] ${STATE_VISUAL_STYLE[signal.state].outline}`} />
      <div className="relative z-10 mx-1 mb-1 -mt-2 flex flex-1 flex-col rounded-xl border border-border bg-card p-5 shadow-[0_3px_10px_rgba(16,47,60,0.12)] transition-colors group-hover:border-primary/35">
        <h2 className="text-sm font-medium leading-snug text-card-foreground group-hover:text-primary">{signal.title}</h2>
        <p className="mt-2 line-clamp-3 text-[13px] leading-relaxed text-muted-foreground">{signal.excerpt}</p>
        <div className="mt-auto border-t border-border pt-4 text-xs text-muted-foreground">
          <p className="font-medium text-foreground">{SOURCE_LABEL[signal.sourceKind]}</p>
          <p className="mt-1 flex items-center gap-1.5"><CalendarClock className="size-3.5" aria-hidden />{formatDate(signal.publishedAt)}</p>
        </div>
      </div>
    </Link>
  )
}

export function buildQueueHref(filters: DetectedFilters): string {
  const search = new URLSearchParams()
  if (filters.state && filters.state !== 'all') search.set('state', filters.state)
  if (filters.sourceKind && filters.sourceKind !== 'all') search.set('source_kind', filters.sourceKind)
  if (filters.query?.trim()) search.set('query', filters.query.trim())
  if (filters.cursor?.trim()) search.set('cursor', filters.cursor.trim())
  if (filters.view) search.set('view', filters.view)
  const value = search.toString()
  return value ? `/?${value}` : '/'
}

function signalHref(signalId: string, returnTo: string): string {
  return `/sinais/${signalId}?${new URLSearchParams({ returnTo })}`
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat('pt-BR', { dateStyle: 'medium', timeStyle: 'short', timeZone: 'America/Manaus' }).format(new Date(value))
}

const SOURCE_LABEL: Record<IndividualSourceKind, string> = { media: 'Mídia', community: 'Relato comunitário' }
const STATE_LABEL: Record<IndividualSignalState, string> = {
  detected: 'Detectado',
  triage: 'Em triagem',
  verification: 'Em verificação',
  risk_assessment: 'Avaliação de risco',
  closed: 'Encerrado',
}
const STATE_VISUAL_STYLE: Record<IndividualSignalState, { banner: string; folder: string; outline: string; line: string; surface: string; rowMarker: string }> = {
  detected: {
    banner: 'bg-[#3E6F9E]', folder: 'bg-[#3E6F9E]/15',
    outline: 'border-[#3E6F9E]', line: 'bg-[#3E6F9E]', surface: 'bg-[#EDF3F8]', rowMarker: 'bg-[#3E6F9E]',
  },
  triage: {
    banner: 'bg-[#47735F]', folder: 'bg-[#47735F]/15',
    outline: 'border-[#47735F]', line: 'bg-[#47735F]', surface: 'bg-[#EDF4F0]', rowMarker: 'bg-[#47735F]',
  },
  verification: {
    banner: 'bg-[#A47B32]', folder: 'bg-[#A47B32]/15',
    outline: 'border-[#A47B32]', line: 'bg-[#A47B32]', surface: 'bg-[#F8F3E7]', rowMarker: 'bg-[#A47B32]',
  },
  risk_assessment: {
    banner: 'bg-[#A6534D]', folder: 'bg-[#A6534D]/15',
    outline: 'border-[#A6534D]', line: 'bg-[#A6534D]', surface: 'bg-[#F8EEEE]', rowMarker: 'bg-[#A6534D]',
  },
  closed: {
    banner: 'bg-[#626970]', folder: 'bg-[#626970]/15',
    outline: 'border-[#626970]', line: 'bg-[#626970]', surface: 'bg-[#F1F2F3]', rowMarker: 'bg-[#626970]',
  },
}

const STATE_ORDER: IndividualSignalState[] = ['detected', 'triage', 'verification', 'risk_assessment', 'closed']
