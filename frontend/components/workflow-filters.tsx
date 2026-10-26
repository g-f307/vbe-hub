'use client'

import { useRouter } from 'next/navigation'
import { useTransition } from 'react'
import { RefreshCw } from 'lucide-react'

import { ActiveFilterChips, FilterControls, SearchField, type QueueFilterState } from '@/components/queue-filters'
import { Button } from '@/components/ui/button'
import { buildQueueSearch, type QueueFilters } from '@/lib/signal-read'
import { cn } from '@/lib/utils'

export function WorkflowFilters({
  filters,
  neighborhoods,
  view,
}: {
  filters: QueueFilterState
  neighborhoods: string[]
  view: 'board' | 'list'
}) {
  const router = useRouter()
  const [isPending, startTransition] = useTransition()

  function navigate(next: QueueFilterState) {
    const search = buildQueueSearch({ ...toQueueFilters(next), page: 1, pageSize: 100 })
    search.set('view', view)
    startTransition(() => router.push(`/kanban?${search.toString()}`))
  }

  return (
    <section aria-label="Filtros do quadro" aria-busy={isPending} className="rounded-md border border-agua bg-mineral p-3 md:p-4">
      <div className="flex items-end gap-2">
        <div className="min-w-0 flex-1 lg:max-w-sm"><SearchField value={filters.search} onChange={(search) => navigate({ ...filters, search })} /></div>
        <div className="hidden min-w-0 flex-[3] lg:block"><FilterControls filters={filters} neighborhoods={neighborhoods} onChange={navigate} /></div>
        <Button variant="ghost" size="icon" onClick={() => startTransition(() => router.refresh())} disabled={isPending} aria-label="Atualizar quadro" className="text-igarape">
          <RefreshCw className={cn(isPending && 'animate-spin')} aria-hidden />
        </Button>
      </div>
      <details className="mt-3 rounded-md border border-agua px-3 py-2 lg:hidden">
        <summary className="cursor-pointer text-sm font-medium text-encontro">Filtros avançados</summary>
        <div className="pt-3"><FilterControls filters={filters} neighborhoods={neighborhoods} onChange={navigate} layout="stack" /></div>
      </details>
      <div className="mt-3"><ActiveFilterChips filters={filters} onChange={navigate} /></div>
    </section>
  )
}

function toQueueFilters(filters: QueueFilterState): QueueFilters {
  return {
    query: filters.search,
    state: filters.state,
    priority: filters.priority,
    district: filters.neighborhood === 'todos' ? undefined : filters.neighborhood,
    sourceType: filters.sourceType,
    period: filters.period,
  }
}
