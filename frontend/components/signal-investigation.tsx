'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { AuditTimeline } from '@/components/audit-timeline'
import { EvidenceThread } from '@/components/evidence-thread'
import { GroupingCriteria } from '@/components/grouping-criteria'
import { SignalHeader } from '@/components/signal-header'
import { SignalStatusStepper } from '@/components/signal-status-stepper'
import { SignalSummary } from '@/components/signal-summary'
import { SourceSheets, type SourceTab } from '@/components/source-sheet'
import { ReviewPanel } from '@/components/review-panel'
import type { ReviewTarget, SignalDetailView } from '@/lib/signal-read'
import type { AuditEvent, GroupingCriterion, Signal, SourceRecord, WorkflowState } from '@/lib/types'
import type { WorkflowOutcome } from '@/lib/workflow-client'

export function SignalInvestigation({
  signal,
  sources,
  criteria,
  audit,
  workflow: initialWorkflow,
  reviewTargets,
}: {
  signal: Signal
  sources: SourceRecord[]
  criteria: GroupingCriterion[]
  audit: AuditEvent[]
  workflow: SignalDetailView['workflow']
  reviewTargets: ReviewTarget[]
}) {
  const [sourceTab, setSourceTab] = useState<SourceTab>('todas')
  const [expandedIds, setExpandedIds] = useState<string[]>([])
  const [workflowOverride, setWorkflowOverride] = useState<SignalDetailView['workflow'] | null>(null)
  const [optimisticAudit, setOptimisticAudit] = useState<AuditEvent[]>([])
  const router = useRouter()
  const workflow = !workflowOverride || initialWorkflow.version > workflowOverride.version ? initialWorkflow : workflowOverride
  const auditEvents = [...optimisticAudit, ...audit.filter((event) => !optimisticAudit.some((pending) => pending.id === event.id))]
  const sourceCounts = signal.sourceCounts ?? { midia: 0, comunidade: 0 }

  function openSource(sourceId: string) {
    setSourceTab('todas')
    setExpandedIds((ids) => (ids.includes(sourceId) ? ids : [...ids, sourceId]))
    window.setTimeout(() => document.getElementById(`ficha-${sourceId}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' }), 0)
  }

  function registerOutcome(outcome: WorkflowOutcome) {
    const state = API_TO_UI_STATE[outcome.workflow.state]
    setWorkflowOverride({ state, version: outcome.workflow.version, updatedAt: outcome.workflow.updated_at })
    setOptimisticAudit((events) => [
      {
        id: outcome.event.id,
        signalId: signal.id,
        at: outcome.event.occurred_at,
        actor: 'analista',
        actorLabel: outcome.event.actor_id,
        title: auditTitle(outcome.event.action),
        description: [outcome.event.reason_code, outcome.event.comment].filter(Boolean).join(' · ') || `Estado do fluxo: ${state}.`,
      },
      ...events.filter((event) => event.id !== outcome.event.id),
    ])
  }

  return (
    <div className="mx-auto flex w-full max-w-[1440px] flex-col gap-5 px-4 py-5 md:px-6 md:py-6 lg:px-8">
      <SignalHeader signal={signal} state={workflow.state} updatedAt={workflow.updatedAt} />
      <SignalStatusStepper current={workflow.state} />

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
          <AuditTimeline events={auditEvents} />
        </div>

        <aside className="sticky top-[76px] flex flex-col gap-4 xl:max-h-[calc(100dvh-92px)] xl:overflow-y-auto xl:pr-1">
          <ReviewPanel signalId={signal.id} workflow={workflow} targets={reviewTargets} onOutcome={registerOutcome} onReload={() => router.refresh()} />
        </aside>
      </div>
    </div>
  )
}

const API_TO_UI_STATE: Record<WorkflowOutcome['workflow']['state'], WorkflowState> = {
  detected: 'detectado',
  triage: 'triagem',
  verification: 'verificacao',
  risk_assessment: 'avaliacao_risco',
  closed: 'encerrado',
}

function auditTitle(action: string): string {
  const titles: Record<string, string> = {
    accept: 'Sugestão aceita',
    correct: 'Sugestão corrigida',
    reject: 'Sugestão rejeitada',
    transition: 'Fluxo atualizado',
  }
  return titles[action] ?? `Ação registrada: ${action}`
}
