import type { Metadata } from 'next'

import { PageHeader } from '@/components/page-header'
import { WorkflowBoard } from '@/components/workflow-board'
import { WorkflowFilters } from '@/components/workflow-filters'
import { buildQueueSearch, filtersFromSearchParams, listSignals } from '@/lib/signal-read'

export const metadata: Metadata = { title: 'Fluxo' }
export const dynamic = 'force-dynamic'

export default async function WorkflowPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>
}) {
  const params = await searchParams
  const filters = filtersFromSearchParams(params)
  const view = first(params.view) === 'list' ? 'list' : 'board'
  const queue = await listSignals({ ...filters, page: 1, pageSize: 100 })
  const neighborhoods = [...new Set(queue.items.map((signal) => signal.neighborhood).filter((value) => value !== 'Não informado'))].sort()
  const canonicalSearch = buildQueueSearch({ ...filters, page: 1, pageSize: 100 })
  canonicalSearch.delete('page')
  canonicalSearch.delete('page_size')

  return (
    <div className="mx-auto flex w-full max-w-[1680px] flex-col gap-5 px-4 py-5 md:px-6 md:py-6 lg:px-8">
      <PageHeader
        title="Fluxo dos sinais"
        description="Acompanhe os mesmos sinais da triagem em seus estágios canônicos, sem alterar estados pelo quadro."
        meta="Leitura operacional · decisões registradas na investigação"
      />
      <WorkflowFilters filters={{
        search: filters.query ?? '',
        state: filters.state ?? 'todos',
        priority: filters.priority ?? 'todas',
        period: filters.period ?? 'todos',
        neighborhood: filters.district ?? 'todos',
        sourceType: filters.sourceType ?? 'todas',
      }} neighborhoods={neighborhoods} view={view} />
      <WorkflowBoard signals={queue.items} total={queue.total} view={view} queryString={canonicalSearch.toString()} />
    </div>
  )
}

function first(value: string | string[] | undefined): string | undefined {
  return Array.isArray(value) ? value[0] : value
}
