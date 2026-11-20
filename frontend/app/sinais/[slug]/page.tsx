import type { Metadata } from 'next'
import { notFound } from 'next/navigation'

import { IndividualSignalDetailView } from '@/components/individual-signal-detail'
import {
  getIndividualSignal,
  getInvestigation,
  IndividualSignalReadError,
  listAllRelatedSignals,
} from '@/lib/individual-signal-read'
import { safeInternalReturnTo } from '@/lib/safe-navigation'
import { resolveSignalTab } from '@/lib/signal-navigation'
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
  let relatedResult
  try {
    ;[signal, relatedResult] = await Promise.all([
      getIndividualSignal(slug),
      listAllRelatedSignals(slug)
        .then((page) => ({ page, unavailable: false }))
        .catch(() => ({
          page: { items: [], nextCursor: null },
          unavailable: true,
        })),
    ])
  } catch (error) {
    if (
      error instanceof IndividualSignalReadError &&
      error.kind === 'not-found'
    )
      notFound()
    throw error
  }
  related = relatedResult.page
  const relatedUnavailable = relatedResult.unavailable
  if (signal.activeInvestigationId)
    investigation = await getInvestigation(signal.activeInvestigationId)
  const requestedTab = first(query.tab)
  const { tab: activeTab, openCandidates } = resolveSignalTab(requestedTab)
  const returnTo = safeInternalReturnTo(first(query.returnTo))

  return (
    <div className="min-h-screen bg-[var(--brand-blue)]">
      <Header />
      <BodySurface>
        <IndividualSignalDetailView
          key={`${signal.id}:${requestedTab}:${first(query.candidates)}`}
          signal={signal}
          related={related}
          returnTo={returnTo}
          activeTab={activeTab}
          initialInvestigation={investigation}
          openCandidates={openCandidates || first(query.candidates) === 'open'}
          relatedUnavailable={relatedUnavailable}
        />
      </BodySurface>
    </div>
  )
}

function first(value: string | string[] | undefined): string | undefined {
  return Array.isArray(value) ? value[0] : value
}
