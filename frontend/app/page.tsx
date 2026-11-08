import type { Metadata } from 'next'

import { DetectedSignalsView, type DetectedFilters } from '@/components/detected-signals'
import {
  listIndividualSignals,
  type IndividualSignalState,
  type IndividualSourceKind,
} from '@/lib/individual-signal-read'
import { Header } from '@/v0/components/header'

export const metadata: Metadata = { title: 'Detectados | VBE Hub' }

export default async function Home({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>
}) {
  const filters = parseDetectedFilters(await searchParams)
  const page = await listIndividualSignals({
    state: filters.state === 'all' ? undefined : filters.state,
    sourceKind: filters.sourceKind === 'all' ? undefined : filters.sourceKind,
    cursor: filters.cursor,
    limit: 24,
  })

  return (
    <div className="min-h-screen bg-background">
      <Header />
      <DetectedSignalsView items={page.items} nextCursor={page.nextCursor} filters={filters} />
    </div>
  )
}

export function parseDetectedFilters(params: Record<string, string | string[] | undefined>): DetectedFilters {
  const state = first(params.state)
  const sourceKind = first(params.source_kind)
  return {
    state: isState(state) ? state : state === 'all' ? 'all' : 'detected',
    sourceKind: isSourceKind(sourceKind) ? sourceKind : 'all',
    query: first(params.query)?.trim() || undefined,
    cursor: first(params.cursor)?.trim() || undefined,
  }
}

function first(value: string | string[] | undefined): string | undefined {
  return Array.isArray(value) ? value[0] : value
}

function isState(value: string | undefined): value is IndividualSignalState {
  return value !== undefined && ['detected', 'triage', 'verification', 'risk_assessment', 'closed'].includes(value)
}

function isSourceKind(value: string | undefined): value is IndividualSourceKind {
  return value === 'media' || value === 'community'
}
