import type { Metadata } from 'next'
import { PageHeader } from '@/components/page-header'
import { QueueIndicators } from '@/components/queue-indicators'
import { SignalQueue } from '@/components/signal-queue'
import { filtersFromSearchParams, listSignals } from '@/lib/signal-read'

export const metadata: Metadata = { title: 'Triagem' }

export default async function TriagePage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>
}) {
  const filters = filtersFromSearchParams(await searchParams)
  const queue = await listSignals(filters)
  const neighborhoods = [...new Set(queue.items.map((signal) => signal.neighborhood).filter((value) => value !== 'Não informado'))].sort()
  const indicators = [
    { key: 'triagem' as const, label: 'Em triagem', value: queue.items.filter((signal) => signal.state === 'triagem').length, trend: 'flat' as const, trendLabel: 'Nesta página' },
    { key: 'verificacao' as const, label: 'Em verificação', value: queue.items.filter((signal) => signal.state === 'verificacao').length, trend: 'flat' as const, trendLabel: 'Nesta página' },
    { key: 'avaliacao_risco' as const, label: 'Em avaliação de risco', value: queue.items.filter((signal) => signal.state === 'avaliacao_risco').length, trend: 'flat' as const, trendLabel: 'Nesta página' },
    { key: 'conflito' as const, label: 'Com divergência', value: 0, trend: 'flat' as const, trendLabel: 'Sem agregação nesta leitura' },
  ]

  return (
    <div className="mx-auto flex w-full max-w-[1440px] flex-col gap-5 px-4 py-5 md:px-6 md:py-6 lg:px-8">
      <PageHeader
        title="Sinais para triagem"
        description="Registros agrupados pelo sistema e prontos para revisão humana."
        meta={`Consulta canônica · página ${queue.page} de ${Math.max(1, Math.ceil(queue.total / queue.pageSize))}`}
      />
      <QueueIndicators indicators={indicators} />
      <SignalQueue signals={queue.items} filters={{
        search: filters.query ?? '', state: filters.state ?? 'todos', priority: filters.priority ?? 'todas', period: filters.period ?? 'todos', neighborhood: filters.district ?? 'todos', sourceType: filters.sourceType ?? 'todas',
      }} page={queue.page} pageSize={queue.pageSize} total={queue.total} neighborhoods={neighborhoods} />
    </div>
  )
}
