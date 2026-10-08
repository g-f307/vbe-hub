'use client'

import Link from 'next/link'
import { useMemo, useState } from 'react'
import { AlertTriangle, ArrowRight, ChevronLeft, ChevronRight, RefreshCw, SearchX, SlidersHorizontal } from 'lucide-react'
import { PriorityBadge, SourceCounts, StateLabel } from '@/components/status-badges'
import { Button } from '@/components/ui/button'
import { Sheet, SheetContent, SheetDescription, SheetFooter, SheetHeader, SheetTitle } from '@/components/ui/sheet'
import { Skeleton } from '@/components/ui/skeleton'
import { formatPeriod, formatRelative, minutesSince } from '@/lib/format'
import { countSourcesByType } from '@/lib/mock-data'
import type { Signal } from '@/lib/types'
import { cn } from '@/lib/utils'
import {
  ActiveFilterChips,
  DEFAULT_FILTERS,
  FilterControls,
  SearchField,
  activeFilterChips,
  type QueueFilterState,
} from '@/components/queue-filters'

const PAGE_SIZE = 6
const PRIORITY_RANK = { urgente: 0, atencao: 1, monitorar: 2, contexto: 3 }
const PERIOD_MINUTES: Record<string, number> = { '24h': 24 * 60, '7d': 7 * 24 * 60, '14d': 14 * 24 * 60 }

type LoadStatus = 'ready' | 'loading' | 'error'

function normalize(text: string) {
  return text.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase()
}

function applyFilters(signals: Signal[], filters: QueueFilterState) {
  const query = normalize(filters.search.trim())
  return signals
    .filter((signal) => {
      if (query) {
        const haystack = normalize(
          [signal.code, signal.title, signal.condition, signal.neighborhood, ...signal.symptoms].join(' '),
        )
        if (!haystack.includes(query)) return false
      }
      if (filters.state !== 'todos' && signal.state !== filters.state) return false
      if (filters.priority !== 'todas' && signal.priority !== filters.priority) return false
      if (filters.neighborhood !== 'todos' && signal.neighborhood !== filters.neighborhood) return false
      if (minutesSince(signal.updatedAt) > PERIOD_MINUTES[filters.period]) return false
      if (filters.sourceType !== 'todas') {
        const counts = countSourcesByType(signal)
        if (filters.sourceType === 'midia' && counts.midia === 0) return false
        if (filters.sourceType === 'comunidade' && counts.comunidade === 0) return false
        if (filters.sourceType === 'ambas' && (counts.midia === 0 || counts.comunidade === 0)) return false
      }
      return true
    })
    .sort((a, b) => PRIORITY_RANK[a.priority] - PRIORITY_RANK[b.priority] || b.updatedAt.localeCompare(a.updatedAt))
}

export function SignalQueue({ signals, initialNeighborhood }: { signals: Signal[]; initialNeighborhood?: string }) {
  const [filters, setFilters] = useState<QueueFilterState>({
    ...DEFAULT_FILTERS,
    neighborhood: initialNeighborhood ?? DEFAULT_FILTERS.neighborhood,
  })
  const [page, setPage] = useState(1)
  const [selectedId, setSelectedId] = useState<string>(signals[0]?.id ?? '')
  const [status, setStatus] = useState<LoadStatus>('ready')
  const [refreshAttempts, setRefreshAttempts] = useState(0)
  const [filtersOpen, setFiltersOpen] = useState(false)

  const filtered = useMemo(() => applyFilters(signals, filters), [signals, filters])
  const pageCount = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE))
  const currentPage = Math.min(page, pageCount)
  const pageItems = filtered.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE)
  const selected = filtered.find((s) => s.id === selectedId) ?? filtered[0]
  const chipCount = activeFilterChips(filters).length

  const updateFilters = (next: QueueFilterState) => {
    setFilters(next)
    setPage(1)
  }

  const refresh = () => {
    setStatus('loading')
    const attempt = refreshAttempts + 1
    setRefreshAttempts(attempt)
    window.setTimeout(() => setStatus(attempt === 1 ? 'error' : 'ready'), 900)
  }

  return (
    <section aria-labelledby="fila-title" className="flex flex-col gap-3">
      <div className="flex flex-col gap-3 rounded-md border border-agua bg-mineral p-3 md:p-4">
        <div className="flex items-end gap-2">
          <h2 id="fila-title" className="sr-only">
            Fila de sinais
          </h2>
          <div className="min-w-0 flex-1 lg:max-w-sm">
            <SearchField value={filters.search} onChange={(search) => updateFilters({ ...filters, search })} />
          </div>
          <Button
            variant="outline"
            className="h-9 lg:hidden"
            onClick={() => setFiltersOpen(true)}
            aria-label={chipCount ? `Filtros, ${chipCount} ativos` : 'Filtros'}
          >
            <SlidersHorizontal aria-hidden />
            <span className="hidden sm:inline">Filtros</span>
            {chipCount > 0 && (
              <span className="flex size-5 items-center justify-center rounded-full bg-igarape text-[11px] text-mineral">
                {chipCount}
              </span>
            )}
          </Button>
          <div className="hidden min-w-0 flex-[3] lg:block">
            <FilterControls filters={filters} onChange={updateFilters} />
          </div>
        </div>
        <ActiveFilterChips filters={filters} onChange={updateFilters} />
      </div>

      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm text-ardosia" aria-live="polite">
          {status === 'loading' ? 'Atualizando fila…' : `${filtered.length} sinais encontrados · ordenados por prioridade sugerida`}
        </p>
        <Button variant="ghost" size="sm" onClick={refresh} disabled={status === 'loading'} className="text-igarape">
          <RefreshCw className={cn(status === 'loading' && 'animate-spin')} aria-hidden />
          Atualizar fila
        </Button>
      </div>

      {status === 'error' && (
        <div role="alert" className="flex flex-col gap-2 rounded-md border border-urucum/40 bg-urucum-soft p-3 sm:flex-row sm:items-center">
          <AlertTriangle className="size-4 shrink-0 text-urucum-ink" aria-hidden />
          <p className="flex-1 text-sm text-urucum-ink">
            Não foi possível atualizar a fila. Os dados exibidos são da última atualização bem-sucedida.
          </p>
          <Button size="sm" variant="outline" onClick={refresh}>
            Tentar novamente
          </Button>
        </div>
      )}

      {status === 'loading' ? (
        <QueueSkeleton />
      ) : filtered.length === 0 ? (
        <EmptyQueue onReset={() => updateFilters(DEFAULT_FILTERS)} />
      ) : (
        <>
          <QueueTable signals={pageItems} selectedId={selected?.id} onSelect={setSelectedId} />
          <QueueCards signals={pageItems} selectedId={selected?.id} onSelect={setSelectedId} />
          <Pagination page={currentPage} pageCount={pageCount} total={filtered.length} onChange={setPage} />
        </>
      )}

      {selected && status !== 'loading' && (
        <div className="fixed inset-x-0 bottom-14 z-30 border-t border-agua bg-mineral/95 p-3 pb-[calc(env(safe-area-inset-bottom)+0.75rem)] md:hidden">
          <Button className="h-11 w-full" render={<Link href={`/sinais/${selected.slug}`} />} nativeButton={false}>
            Revisar {selected.code}
            <ArrowRight aria-hidden />
          </Button>
        </div>
      )}

      <Sheet open={filtersOpen} onOpenChange={setFiltersOpen}>
        <SheetContent side="bottom" className="max-h-[85dvh] overflow-y-auto rounded-t-lg">
          <SheetHeader>
            <SheetTitle>Filtros da fila</SheetTitle>
            <SheetDescription>{filtered.length} sinais com os filtros atuais.</SheetDescription>
          </SheetHeader>
          <div className="px-4">
            <FilterControls filters={filters} onChange={updateFilters} layout="stack" />
          </div>
          <SheetFooter className="flex-row gap-2">
            <Button variant="outline" className="h-11 flex-1" onClick={() => updateFilters(DEFAULT_FILTERS)}>
              Limpar
            </Button>
            <Button className="h-11 flex-1" onClick={() => setFiltersOpen(false)}>
              Ver {filtered.length} sinais
            </Button>
          </SheetFooter>
        </SheetContent>
      </Sheet>
    </section>
  )
}

function QueueTable({
  signals,
  selectedId,
  onSelect,
}: {
  signals: Signal[]
  selectedId?: string
  onSelect: (id: string) => void
}) {
  return (
    <div className="hidden overflow-hidden rounded-md border border-agua bg-mineral md:block">
      <table className="w-full border-collapse text-left">
        <caption className="sr-only">
          Sinais para triagem, ordenados por prioridade sugerida. Selecione uma linha para destacar o sinal.
        </caption>
        <thead className="bg-nevoa text-xs text-ardosia">
          <tr>
            <th scope="col" className="px-4 py-2.5 font-medium">Sinal</th>
            <th scope="col" className="px-3 py-2.5 font-medium">Evidências</th>
            <th scope="col" className="px-3 py-2.5 font-medium">Localização</th>
            <th scope="col" className="hidden px-3 py-2.5 font-medium xl:table-cell">Período</th>
            <th scope="col" className="px-3 py-2.5 font-medium">Prioridade sugerida</th>
            <th scope="col" className="hidden px-3 py-2.5 font-medium lg:table-cell">Estado</th>
            <th scope="col" className="hidden px-3 py-2.5 font-medium xl:table-cell">Atualizado</th>
            <th scope="col" className="px-4 py-2.5 font-medium">
              <span className="sr-only">Ação</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {signals.map((signal) => {
            const counts = countSourcesByType(signal)
            const isSelected = signal.id === selectedId
            return (
              <tr
                key={signal.id}
                onClick={() => onSelect(signal.id)}
                onFocusCapture={() => onSelect(signal.id)}
                aria-selected={isSelected}
                className={cn(
                  'cursor-pointer border-t border-agua align-top transition-colors hover:bg-nevoa',
                  isSelected && 'bg-vitoria-soft/45 shadow-[inset_3px_0_0_#14736f] hover:bg-vitoria-soft/60',
                )}
              >
                <td className="max-w-80 px-4 py-3">
                  <p className="font-mono text-xs text-ardosia">{signal.code}</p>
                  <p className="mt-0.5 text-sm font-semibold text-encontro text-pretty">{signal.title}</p>
                  <p className="mt-0.5 text-xs text-ardosia">{signal.condition}</p>
                </td>
                <td className="px-3 py-3">
                  <p className="text-sm font-medium whitespace-nowrap text-grafite">
                    {signal.sourceIds.length} {signal.sourceIds.length === 1 ? 'fonte' : 'fontes'}
                  </p>
                  <SourceCounts media={counts.midia} community={counts.comunidade} />
                </td>
                <td className="px-3 py-3 text-sm text-grafite">
                  {signal.neighborhood}
                  <span className="block text-xs text-ardosia">{signal.municipality}</span>
                </td>
                <td className="hidden px-3 py-3 text-sm whitespace-nowrap text-grafite xl:table-cell">
                  {formatPeriod(signal.periodStart, signal.periodEnd)}
                </td>
                <td className="px-3 py-3">
                  <PriorityBadge priority={signal.priority} showSuggested={false} />
                </td>
                <td className="hidden px-3 py-3 lg:table-cell">
                  <StateLabel state={signal.state} />
                </td>
                <td className="hidden px-3 py-3 text-sm whitespace-nowrap text-ardosia xl:table-cell">
                  {formatRelative(signal.updatedAt)}
                </td>
                <td className="px-4 py-3 text-right">
                  <Link
                    href={`/sinais/${signal.slug}`}
                    className="inline-flex h-8 items-center gap-1 rounded-md px-2 text-sm font-medium whitespace-nowrap text-igarape hover:bg-vitoria-soft hover:text-igarape-ink"
                  >
                    Revisar sinal
                    <span className="sr-only"> {signal.code}</span>
                    <ArrowRight className="size-4" aria-hidden />
                  </Link>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

function QueueCards({
  signals,
  selectedId,
  onSelect,
}: {
  signals: Signal[]
  selectedId?: string
  onSelect: (id: string) => void
}) {
  return (
    <ul className="flex flex-col gap-2 md:hidden" aria-label="Sinais para triagem">
      {signals.map((signal) => {
        const counts = countSourcesByType(signal)
        const isSelected = signal.id === selectedId
        return (
          <li key={signal.id}>
            <button
              type="button"
              onClick={() => onSelect(signal.id)}
              aria-pressed={isSelected}
              className={cn(
                'flex w-full flex-col gap-2 rounded-md border bg-mineral p-3 text-left',
                isSelected ? 'border-igarape shadow-[inset_3px_0_0_#14736f]' : 'border-agua',
              )}
            >
              <div className="flex items-center justify-between gap-2">
                <span className="font-mono text-xs text-ardosia">{signal.code}</span>
                <PriorityBadge priority={signal.priority} showSuggested={false} withTooltip={false} />
              </div>
              <span className="text-sm font-semibold text-encontro text-pretty">{signal.title}</span>
              <span className="text-xs text-ardosia">
                {signal.neighborhood} · {formatPeriod(signal.periodStart, signal.periodEnd)}
              </span>
              <span className="flex flex-wrap items-center justify-between gap-2">
                <SourceCounts media={counts.midia} community={counts.comunidade} />
                <StateLabel state={signal.state} className="text-xs" />
              </span>
            </button>
          </li>
        )
      })}
    </ul>
  )
}

function Pagination({
  page,
  pageCount,
  total,
  onChange,
}: {
  page: number
  pageCount: number
  total: number
  onChange: (page: number) => void
}) {
  const start = (page - 1) * PAGE_SIZE + 1
  const end = Math.min(page * PAGE_SIZE, total)
  return (
    <nav aria-label="Paginação da fila" className="flex items-center justify-between gap-2">
      <p className="text-sm text-ardosia">
        {start}–{end} de {total}
      </p>
      <div className="flex items-center gap-1">
        <Button
          variant="outline"
          size="icon"
          className="size-11 md:size-8"
          onClick={() => onChange(page - 1)}
          disabled={page <= 1}
          aria-label="Página anterior"
        >
          <ChevronLeft aria-hidden />
        </Button>
        <span className="px-2 text-sm text-grafite" aria-current="page">
          {page} / {pageCount}
        </span>
        <Button
          variant="outline"
          size="icon"
          className="size-11 md:size-8"
          onClick={() => onChange(page + 1)}
          disabled={page >= pageCount}
          aria-label="Próxima página"
        >
          <ChevronRight aria-hidden />
        </Button>
      </div>
    </nav>
  )
}

function QueueSkeleton() {
  return (
    <div className="flex flex-col gap-2 rounded-md border border-agua bg-mineral p-4" aria-hidden>
      {Array.from({ length: 5 }).map((_, i) => (
        <div key={i} className="flex items-center gap-4 py-2">
          <div className="flex flex-1 flex-col gap-1.5">
            <Skeleton className="h-3 w-24" />
            <Skeleton className="h-4 w-3/5" />
          </div>
          <Skeleton className="hidden h-4 w-20 md:block" />
          <Skeleton className="h-6 w-20" />
        </div>
      ))}
    </div>
  )
}

function EmptyQueue({ onReset }: { onReset: () => void }) {
  return (
    <div className="flex flex-col items-center gap-3 rounded-md border border-dashed border-agua-strong bg-mineral px-6 py-12 text-center">
      <SearchX className="size-6 text-ardosia" aria-hidden />
      <div>
        <p className="text-sm font-semibold text-encontro">Nenhum sinal encontrado com os filtros atuais.</p>
        <p className="mt-1 text-sm text-ardosia">Amplie o período ou remova filtros para ver mais sinais.</p>
      </div>
      <Button variant="outline" onClick={onReset}>
        Limpar filtros
      </Button>
    </div>
  )
}
