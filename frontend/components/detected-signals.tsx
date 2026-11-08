import Link from 'next/link'
import { CalendarClock, ChevronRight, Filter, Inbox, Newspaper, Radio, Search } from 'lucide-react'

import type {
  IndividualSignalCard,
  IndividualSignalState,
  IndividualSourceKind,
} from '@/lib/individual-signal-read'
import { Badge } from '@/v0/components/ui/badge'

export type DetectedFilters = {
  state?: IndividualSignalState | 'all'
  sourceKind?: IndividualSourceKind | 'all'
  query?: string
  cursor?: string
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
  const normalizedQuery = filters.query?.trim().toLocaleLowerCase('pt-BR') ?? ''
  const visibleItems = normalizedQuery
    ? items.filter((signal) => [signal.title, signal.excerpt, signal.sourceName].some((value) => value.toLocaleLowerCase('pt-BR').includes(normalizedQuery)))
    : items
  return (
    <main id="conteudo-principal" className="mx-auto w-full max-w-screen-2xl px-4 py-6 sm:px-6 lg:px-8">
      <div className="flex flex-col gap-3 border-b border-border pb-5 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-sm font-medium text-primary">Entrada da vigilância</p>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight text-foreground sm:text-3xl">Sinais detectados</h1>
          <p className="mt-2 max-w-3xl text-sm leading-relaxed text-muted-foreground">
            Cada card corresponde a uma única notícia ou relato comunitário. Abra o sinal para conferir a fonte e as sugestões relacionadas.
          </p>
        </div>
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Inbox className="size-4 text-primary" aria-hidden />
          <strong className="font-semibold text-foreground">{visibleItems.length}</strong> sinais nesta página
        </div>
      </div>

      <form action="/" method="get" className="mt-5 grid gap-3 rounded-xl border border-border bg-card p-4 shadow-sm md:grid-cols-[minmax(240px,1fr)_200px_200px_auto]">
        <label className="relative block">
          <span className="sr-only">Buscar nesta página</span>
          <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" aria-hidden />
          <input
            name="query"
            defaultValue={filters.query ?? ''}
            placeholder="Buscar no lote carregado"
            className="h-11 w-full rounded-md border border-input bg-background pl-10 pr-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
          />
        </label>
        <label>
          <span className="sr-only">Estado do fluxo</span>
          <select name="state" defaultValue={filters.state ?? 'detected'} className="h-11 w-full rounded-md border border-input bg-background px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring">
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
          <select name="source_kind" defaultValue={filters.sourceKind ?? 'all'} className="h-11 w-full rounded-md border border-input bg-background px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring">
            <option value="all">Todas as fontes</option>
            <option value="media">Mídia</option>
            <option value="community">Relato comunitário</option>
          </select>
        </label>
        <button type="submit" className="inline-flex min-h-11 items-center justify-center gap-2 rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2">
          <Filter className="size-4" aria-hidden /> Aplicar
        </button>
      </form>

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
      ) : (
        <section aria-label="Lista de sinais" className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {visibleItems.map((signal) => (
            <DetectedCard key={signal.id} signal={signal} returnTo={returnTo} />
          ))}
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

function DetectedCard({ signal, returnTo }: { signal: IndividualSignalCard; returnTo: string }) {
  const Icon = signal.sourceKind === 'media' ? Newspaper : Radio
  const params = new URLSearchParams({ returnTo })
  return (
    <Link
      href={`/sinais/${signal.id}?${params}`}
      aria-label={`Abrir sinal ${signal.title}`}
      className="group flex min-h-64 flex-col rounded-xl border border-border bg-card p-5 shadow-sm transition-[border-color,box-shadow] hover:border-primary/40 hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
    >
      <div className="flex items-start justify-between gap-3">
        <Badge variant="outline" className="gap-1.5 bg-background"><Icon className="size-3.5" aria-hidden />{SOURCE_LABEL[signal.sourceKind]}</Badge>
        <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${STATE_STYLE[signal.state]}`}>{STATE_LABEL[signal.state]}</span>
      </div>
      <h2 className="mt-4 text-base font-semibold leading-snug text-card-foreground group-hover:text-primary">{signal.title}</h2>
      <p className="mt-2 line-clamp-3 text-sm leading-relaxed text-muted-foreground">{signal.excerpt}</p>
      <div className="mt-auto border-t border-border pt-4 text-xs text-muted-foreground">
        <p className="truncate font-medium text-foreground">{signal.sourceName}</p>
        <p className="mt-1 flex items-center gap-1.5"><CalendarClock className="size-3.5" aria-hidden />{formatDate(signal.publishedAt)}</p>
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
  const value = search.toString()
  return value ? `/?${value}` : '/'
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
const STATE_STYLE: Record<IndividualSignalState, string> = {
  detected: 'bg-blue-100 text-blue-800',
  triage: 'bg-amber-100 text-amber-800',
  verification: 'bg-cyan-100 text-cyan-800',
  risk_assessment: 'bg-orange-100 text-orange-800',
  closed: 'bg-slate-100 text-slate-700',
}
