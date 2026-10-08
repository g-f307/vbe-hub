'use client'

import { useState } from 'react'
import { CircleAlert, FileCheck2 } from 'lucide-react'
import { AuditTimeline } from '@/components/audit-timeline'
import { EvidenceThread } from '@/components/evidence-thread'
import { GroupingCriteria } from '@/components/grouping-criteria'
import { SignalHeader } from '@/components/signal-header'
import { SignalStatusStepper } from '@/components/signal-status-stepper'
import { SignalSummary } from '@/components/signal-summary'
import { SourceSheets, type SourceTab } from '@/components/source-sheet'
import type { AuditEvent, GroupingCriterion, Signal, SourceRecord } from '@/lib/types'

export function SignalInvestigation({
  signal,
  sources,
  criteria,
  audit,
}: {
  signal: Signal
  sources: SourceRecord[]
  criteria: GroupingCriterion[]
  audit: AuditEvent[]
}) {
  const [sourceTab, setSourceTab] = useState<SourceTab>('todas')
  const [expandedIds, setExpandedIds] = useState<string[]>([])
  const sourceCounts = signal.sourceCounts ?? { midia: 0, comunidade: 0 }

  function openSource(sourceId: string) {
    setSourceTab('todas')
    setExpandedIds((ids) => (ids.includes(sourceId) ? ids : [...ids, sourceId]))
    window.setTimeout(() => document.getElementById(`ficha-${sourceId}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' }), 0)
  }

  return (
    <div className="mx-auto flex w-full max-w-[1440px] flex-col gap-5 px-4 py-5 md:px-6 md:py-6 lg:px-8">
      <SignalHeader signal={signal} state={signal.state} updatedAt={signal.updatedAt} />
      <SignalStatusStepper current={signal.state} />

      <div className="grid items-start gap-5 xl:grid-cols-[minmax(0,1fr)_360px]">
        <div className="flex min-w-0 flex-col gap-5">
          <SignalSummary signal={signal} sourceCounts={sourceCounts} />
          <EvidenceThread signal={signal} sources={sources} removedIds={[]} onOpenSheet={openSource} />
          <GroupingCriteria criteria={criteria} />
          <SourceSheets
            sources={sources}
            removedIds={[]}
            tab={sourceTab}
            onTabChange={setSourceTab}
            expandedIds={expandedIds}
            onExpandedChange={(id, open) => setExpandedIds((ids) => (open ? [...new Set([...ids, id])] : ids.filter((item) => item !== id)))}
          />
          <AuditTimeline events={audit} />
        </div>

        <aside className="sticky top-[76px] flex flex-col gap-4 xl:max-h-[calc(100dvh-92px)] xl:overflow-y-auto xl:pr-1">
          <section aria-labelledby="decisao-titulo" className="rounded-md border border-encontro/25 bg-mineral">
            <div className="border-b border-agua px-4 py-3">
              <h2 id="decisao-titulo" className="text-base font-semibold text-encontro">Decisão do analista</h2>
              <p className="mt-1 text-sm text-ardosia">Revise as fontes e sugestões antes de qualquer ação.</p>
            </div>
            <div className="flex gap-3 p-4">
              <span className="flex size-9 shrink-0 items-center justify-center rounded-md bg-vitoria-soft text-igarape-ink"><FileCheck2 className="size-4" aria-hidden /></span>
              <div>
                <p className="text-sm font-medium text-grafite">Leitura disponível; registro de decisão em preparação</p>
                <p className="mt-1 text-sm leading-relaxed text-ardosia">Esta etapa consulta dados persistidos, mas não altera o workflow. O registro auditável de decisões humanas será conectado separadamente.</p>
              </div>
            </div>
            <div className="mx-4 mb-4 flex gap-2 rounded-sm bg-nevoa px-3 py-2.5 text-xs leading-relaxed text-ardosia">
              <CircleAlert className="mt-0.5 size-4 shrink-0 text-andiroba-ink" aria-hidden />
              Prioridade, extração e correlação são sugestões auditáveis; não confirmam doença, surto ou decisão sanitária.
            </div>
          </section>
        </aside>
      </div>
    </div>
  )
}
