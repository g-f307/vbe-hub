import type { Metadata } from 'next'
import { notFound } from 'next/navigation'

import { IndividualSignalDetailView } from '@/components/individual-signal-detail'
import {
  getIndividualSignal,
  getInvestigation,
  IndividualSignalReadError,
  listRelatedSignals,
} from '@/lib/individual-signal-read'
import { safeInternalReturnTo } from '@/lib/safe-navigation'
import { Header } from '@/v0/components/header'
import { BodySurface } from '@/v0/components/body-surface'

export const metadata: Metadata = { title: 'Investigar sinal | VBE Hub' }

export default async function SignalPage({
  params,
  searchParams,
}: {
  params: Promise<{ slug: string }>
  searchParams: Promise<Record<string, string | string[] | undefined>>
}) {
  const [{ slug }, query] = await Promise.all([params, searchParams])
  let signal
  let related
  let investigation = null
  try {
    ;[signal, related] = await Promise.all([
      getIndividualSignal(slug),
      listRelatedSignals(slug),
    ])
  } catch (error) {
    if (error instanceof IndividualSignalReadError && error.kind === 'not-found') notFound()
    throw error
  }
  if (signal.activeInvestigationId) investigation = await getInvestigation(signal.activeInvestigationId)
  const requestedTab = first(query.tab)
  const activeTab = requestedTab === 'related' || requestedTab === 'evidence' ? requestedTab : 'overview'
  const returnTo = safeInternalReturnTo(first(query.returnTo))

  return (
    <div className="min-h-screen bg-primary">
      <Header />
      <BodySurface>
        <IndividualSignalDetailView signal={signal} related={related} returnTo={returnTo} activeTab={activeTab} initialInvestigation={investigation} />
      </BodySurface>
    </div>
  )
}

function first(value: string | string[] | undefined): string | undefined {
  return Array.isArray(value) ? value[0] : value
}
