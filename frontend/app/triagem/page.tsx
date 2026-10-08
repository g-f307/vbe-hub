import type { Metadata } from 'next'
import { PageHeader } from '@/components/page-header'
import { QueueIndicators } from '@/components/queue-indicators'
import { SignalQueue } from '@/components/signal-queue'
import { formatDateTime } from '@/lib/format'
import { LAST_UPDATED_ISO, MUNICIPALITY, NEIGHBORHOOD_NAMES, QUEUE_INDICATORS, SIGNALS } from '@/lib/mock-data'

export const metadata: Metadata = { title: 'Triagem' }

export default async function TriagePage({
  searchParams,
}: {
  searchParams: Promise<{ bairro?: string }>
}) {
  const { bairro } = await searchParams
  const initialNeighborhood = bairro && NEIGHBORHOOD_NAMES.includes(bairro) ? bairro : undefined

  return (
    <div className="mx-auto flex w-full max-w-[1440px] flex-col gap-5 px-4 py-5 md:px-6 md:py-6 lg:px-8">
      <PageHeader
        title="Sinais para triagem"
        description="Registros agrupados pelo sistema e prontos para revisão humana."
        meta={`${MUNICIPALITY}, AM · Atualizado em ${formatDateTime(LAST_UPDATED_ISO)}`}
      />
      <QueueIndicators indicators={QUEUE_INDICATORS} />
      <SignalQueue signals={SIGNALS} initialNeighborhood={initialNeighborhood} />
    </div>
  )
}
