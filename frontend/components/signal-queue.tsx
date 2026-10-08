'use client'

import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useState, useTransition } from 'react'
import { ArrowRight, ChevronLeft, ChevronRight, RefreshCw, SearchX, SlidersHorizontal } from 'lucide-react'
import { ActiveFilterChips, FilterControls, SearchField, activeFilterChips, type QueueFilterState } from '@/components/queue-filters'
import { PriorityBadge, SourceCounts, StateLabel } from '@/components/status-badges'
import { Button } from '@/components/ui/button'
import { Sheet, SheetContent, SheetDescription, SheetFooter, SheetHeader, SheetTitle } from '@/components/ui/sheet'
import { Skeleton } from '@/components/ui/skeleton'
import { formatPeriod } from '@/lib/format'
import { buildQueueSearch, type QueueFilters } from '@/lib/signal-read'
import type { Signal } from '@/lib/types'
import { cn } from '@/lib/utils'

export function SignalQueue({ signals, filters, page, pageSize, total, neighborhoods }: { signals: Signal[]; filters: QueueFilterState; page: number; pageSize: number; total: number; neighborhoods: string[] }) {
  const router = useRouter()
  const [selectedId, setSelectedId] = useState<string>(signals[0]?.id ?? '')
  const [filtersOpen, setFiltersOpen] = useState(false)
  const [isPending, startTransition] = useTransition()
  const selected = signals.find((signal) => signal.id === selectedId) ?? signals[0]
  const pageCount = Math.max(1, Math.ceil(total / pageSize))
  const chipCount = activeFilterChips(filters).length

  const navigate = (next: QueueFilterState) => {
    const search = buildQueueSearch({ ...toQueueFilters(next), page: 1 })
    startTransition(() => router.push(`/triagem?${search.toString()}`))
  }
  const changePage = (nextPage: number) => {
    const search = buildQueueSearch({ ...toQueueFilters(filters), page: nextPage })
    startTransition(() => router.push(`/triagem?${search.toString()}`))
  }

  return (
    <section aria-labelledby="fila-title" className="flex flex-col gap-3" aria-busy={isPending}>
      <div className="flex flex-col gap-3 rounded-md border border-agua bg-mineral p-3 md:p-4">
        <div className="flex items-end gap-2">
          <h2 id="fila-title" className="sr-only">Fila de sinais</h2>
          <div className="min-w-0 flex-1 lg:max-w-sm"><SearchField value={filters.search} onChange={(search) => navigate({ ...filters, search })} /></div>
          <Button variant="outline" className="h-9 lg:hidden" onClick={() => setFiltersOpen(true)} aria-label={chipCount ? `Filtros, ${chipCount} ativos` : 'Filtros'}>
            <SlidersHorizontal aria-hidden /><span className="hidden sm:inline">Filtros</span>
            {chipCount > 0 && <span className="flex size-5 items-center justify-center rounded-full bg-igarape text-[11px] text-mineral">{chipCount}</span>}
          </Button>
          <div className="hidden min-w-0 flex-[3] lg:block"><FilterControls filters={filters} neighborhoods={neighborhoods} onChange={navigate} /></div>
        </div>
        <ActiveFilterChips filters={filters} onChange={navigate} />
      </div>

      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm text-ardosia" aria-live="polite">{isPending ? 'Atualizando fila…' : `${total} ${total === 1 ? 'sinal encontrado' : 'sinais encontrados'} · ordenados por prioridade sugerida`}</p>
        <Button variant="ghost" size="sm" onClick={() => startTransition(() => router.refresh())} disabled={isPending} className="text-igarape"><RefreshCw className={cn(isPending && 'animate-spin')} aria-hidden />Atualizar fila</Button>
      </div>

      {isPending ? <QueueSkeleton /> : signals.length === 0 ? <EmptyQueue onReset={() => navigate(DEFAULT_QUEUE_FILTERS)} /> : <>
        <QueueTable signals={signals} selectedId={selected?.id} onSelect={setSelectedId} />
        <QueueCards signals={signals} selectedId={selected?.id} onSelect={setSelectedId} />
        <Pagination page={page} pageCount={pageCount} total={total} pageSize={pageSize} onChange={changePage} />
      </>}

      {selected && !isPending && <div className="fixed inset-x-0 bottom-14 z-30 border-t border-agua bg-mineral/95 p-3 pb-[calc(env(safe-area-inset-bottom)+0.75rem)] md:hidden"><Button className="h-11 w-full" render={<Link href={`/sinais/${selected.id}`} />} nativeButton={false}>Revisar sinal<ArrowRight aria-hidden /></Button></div>}

      <Sheet open={filtersOpen} onOpenChange={setFiltersOpen}><SheetContent side="bottom" className="max-h-[85dvh] overflow-y-auto rounded-t-lg"><SheetHeader><SheetTitle>Filtros da fila</SheetTitle><SheetDescription>{total} sinais com os filtros atuais.</SheetDescription></SheetHeader><div className="px-4"><FilterControls filters={filters} neighborhoods={neighborhoods} onChange={navigate} layout="stack" /></div><SheetFooter className="flex-row gap-2"><Button variant="outline" className="h-11 flex-1" onClick={() => navigate(DEFAULT_QUEUE_FILTERS)}>Limpar</Button><Button className="h-11 flex-1" onClick={() => setFiltersOpen(false)}>Ver {total} sinais</Button></SheetFooter></SheetContent></Sheet>
    </section>
  )
}

const DEFAULT_QUEUE_FILTERS: QueueFilterState = { search: '', state: 'todos', priority: 'todas', period: 'todos', neighborhood: 'todos', sourceType: 'todas' }

function toQueueFilters(filters: QueueFilterState): QueueFilters {
  return { query: filters.search, state: filters.state, priority: filters.priority, district: filters.neighborhood === 'todos' ? undefined : filters.neighborhood, sourceType: filters.sourceType as QueueFilters['sourceType'], period: filters.period }
}

function QueueTable({ signals, selectedId, onSelect }: { signals: Signal[]; selectedId?: string; onSelect: (id: string) => void }) {
  return <div className="hidden overflow-hidden rounded-md border border-agua bg-mineral md:block"><table className="w-full border-collapse text-left"><caption className="sr-only">Sinais para triagem, ordenados por prioridade sugerida. Selecione uma linha para destacar o sinal.</caption><thead className="bg-nevoa text-xs text-ardosia"><tr><th scope="col" className="px-4 py-2.5 font-medium">Sinal</th><th scope="col" className="px-3 py-2.5 font-medium">Evidências</th><th scope="col" className="px-3 py-2.5 font-medium">Localização</th><th scope="col" className="hidden px-3 py-2.5 font-medium xl:table-cell">Período</th><th scope="col" className="px-3 py-2.5 font-medium">Prioridade sugerida</th><th scope="col" className="hidden px-3 py-2.5 font-medium lg:table-cell">Estado</th><th scope="col" className="px-4 py-2.5 font-medium"><span className="sr-only">Ação</span></th></tr></thead><tbody>{signals.map((signal) => <QueueRow key={signal.id} signal={signal} selected={signal.id === selectedId} onSelect={onSelect} />)}</tbody></table></div>
}

function QueueRow({ signal, selected, onSelect }: { signal: Signal; selected: boolean; onSelect: (id: string) => void }) {
  const counts = signal.sourceCounts ?? { midia: 0, comunidade: 0, total: 0 }
  return <tr onClick={() => onSelect(signal.id)} onFocusCapture={() => onSelect(signal.id)} aria-selected={selected} className={cn('cursor-pointer border-t border-agua align-top transition-colors hover:bg-nevoa', selected && 'bg-vitoria-soft/45 shadow-[inset_3px_0_0_#14736f] hover:bg-vitoria-soft/60')}><td className="max-w-80 px-4 py-3"><p className="font-mono text-xs text-ardosia">{signal.code}</p><p className="mt-0.5 text-sm font-semibold text-encontro text-pretty">{signal.title}</p><p className="mt-0.5 text-xs text-ardosia">{signal.condition}</p></td><td className="px-3 py-3"><p className="text-sm font-medium whitespace-nowrap text-grafite">{counts.total} {counts.total === 1 ? 'fonte' : 'fontes'}</p><SourceCounts media={counts.midia} community={counts.comunidade} /></td><td className="px-3 py-3 text-sm text-grafite">{signal.neighborhood}<span className="block text-xs text-ardosia">{signal.municipality}</span></td><td className="hidden px-3 py-3 text-sm whitespace-nowrap text-grafite xl:table-cell">{formatPeriod(signal.periodStart, signal.periodEnd)}</td><td className="px-3 py-3"><PriorityBadge priority={signal.priority} showSuggested={false} /></td><td className="hidden px-3 py-3 lg:table-cell"><StateLabel state={signal.state} /></td><td className="px-4 py-3 text-right"><Link href={`/sinais/${signal.id}`} className="inline-flex h-8 items-center gap-1 rounded-md px-2 text-sm font-medium whitespace-nowrap text-igarape hover:bg-vitoria-soft hover:text-igarape-ink">Revisar sinal<span className="sr-only"> {signal.code}</span><ArrowRight className="size-4" aria-hidden /></Link></td></tr>
}

function QueueCards({ signals, selectedId, onSelect }: { signals: Signal[]; selectedId?: string; onSelect: (id: string) => void }) {
  return <ul className="flex flex-col gap-2 md:hidden" aria-label="Sinais para triagem">{signals.map((signal) => { const counts = signal.sourceCounts ?? { midia: 0, comunidade: 0 }; return <li key={signal.id}><button type="button" onClick={() => onSelect(signal.id)} aria-pressed={signal.id === selectedId} className={cn('flex w-full flex-col gap-2 rounded-md border bg-mineral p-3 text-left', signal.id === selectedId ? 'border-igarape shadow-[inset_3px_0_0_#14736f]' : 'border-agua')}><div className="flex items-center justify-between gap-2"><span className="font-mono text-xs text-ardosia">{signal.code}</span><PriorityBadge priority={signal.priority} showSuggested={false} withTooltip={false} /></div><span className="text-sm font-semibold text-encontro text-pretty">{signal.title}</span><span className="text-xs text-ardosia">{signal.neighborhood} · {formatPeriod(signal.periodStart, signal.periodEnd)}</span><span className="flex flex-wrap items-center justify-between gap-2"><SourceCounts media={counts.midia} community={counts.comunidade} /><StateLabel state={signal.state} className="text-xs" /></span></button></li> })}</ul>
}

function Pagination({ page, pageCount, total, pageSize, onChange }: { page: number; pageCount: number; total: number; pageSize: number; onChange: (page: number) => void }) {
  const start = total === 0 ? 0 : (page - 1) * pageSize + 1
  const end = Math.min(page * pageSize, total)
  return <nav aria-label="Paginação da fila" className="flex items-center justify-between gap-2"><p className="text-sm text-ardosia">{start}–{end} de {total}</p><div className="flex items-center gap-1"><Button variant="outline" size="icon-sm" onClick={() => onChange(page - 1)} disabled={page <= 1} aria-label="Página anterior"><ChevronLeft aria-hidden /></Button><span className="min-w-20 text-center text-sm text-ardosia">Página {page} de {pageCount}</span><Button variant="outline" size="icon-sm" onClick={() => onChange(page + 1)} disabled={page >= pageCount} aria-label="Próxima página"><ChevronRight aria-hidden /></Button></div></nav>
}

function EmptyQueue({ onReset }: { onReset: () => void }) {
  return <div className="flex flex-col items-center gap-2 rounded-md border border-dashed border-agua-strong bg-nevoa/60 px-5 py-12 text-center"><SearchX className="size-6 text-ardosia" aria-hidden /><h3 className="text-sm font-semibold text-encontro">Nenhum sinal corresponde aos filtros</h3><p className="max-w-md text-sm text-ardosia">A consulta foi executada na API canônica e não retornou sinais para estes critérios.</p><Button variant="outline" size="sm" onClick={onReset}>Limpar filtros</Button></div>
}

function QueueSkeleton() {
  return <div className="overflow-hidden rounded-md border border-agua bg-mineral p-4"><Skeleton className="h-8 w-full" /><div className="mt-3 grid gap-3">{Array.from({ length: 4 }, (_, index) => <Skeleton key={index} className="h-16 w-full" />)}</div></div>
}
