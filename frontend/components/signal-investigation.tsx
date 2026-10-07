'use client'

import { useMemo, useState } from 'react'
import { Check, CircleAlert, FilePenLine, SendHorizontal, X } from 'lucide-react'
import { toast } from 'sonner'
import { AuditTimeline } from '@/components/audit-timeline'
import { EvidenceThread } from '@/components/evidence-thread'
import { GroupingCriteria } from '@/components/grouping-criteria'
import { SignalHeader } from '@/components/signal-header'
import { SignalStatusStepper } from '@/components/signal-status-stepper'
import { SignalSummary } from '@/components/signal-summary'
import { SourceSheets, type SourceTab } from '@/components/source-sheet'
import { StateLabel } from '@/components/status-badges'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { buildAuditTrail, countSourcesByType, getSourcesForSignal } from '@/lib/mock-data'
import { DECISION_LABEL, nextStepLabel, resolveResultingState } from '@/lib/review'
import type { NextStep, ReviewDecision, ReviewDecisionType, Signal, WorkflowState } from '@/lib/types'
import { cn } from '@/lib/utils'

const DECISION_OPTIONS: { value: ReviewDecisionType; icon: typeof Check; description: string }[] = [
  { value: 'aceitar', icon: Check, description: 'Mantém as evidências vinculadas ao sinal.' },
  { value: 'corrigir', icon: FilePenLine, description: 'Permite retirar evidências que não pertencem ao agrupamento.' },
  { value: 'rejeitar', icon: X, description: 'Encerra o agrupamento como não confirmado pela revisão.' },
]

function nextStepForTarget(current: WorkflowState, target: WorkflowState): NextStep {
  if (target === 'encerrado') return 'encerrar'
  return target === current ? 'manter' : 'avancar'
}

export function SignalInvestigation({ signal }: { signal: Signal }) {
  const sources = useMemo(() => getSourcesForSignal(signal.id), [signal.id])
  const [state, setState] = useState(signal.state)
  const [decision, setDecision] = useState<ReviewDecisionType>('aceitar')
  const [nextStep, setNextStep] = useState<NextStep>('manter')
  const [removedIds, setRemovedIds] = useState<string[]>([])
  const [comment, setComment] = useState('')
  const [lastDecision, setLastDecision] = useState<ReviewDecision | undefined>()
  const [sourceTab, setSourceTab] = useState<SourceTab>('todas')
  const [expandedIds, setExpandedIds] = useState<string[]>([])

  const resultingState = resolveResultingState(state, nextStep)
  const auditTrail = useMemo(
    () => (lastDecision ? [...buildAuditTrail(signal), { ...buildAuditTrail(signal).at(-1)!, id: 'demo-review', actor: 'analista' as const, title: 'Decisão registrada na demonstração', description: DECISION_LABEL[lastDecision.type], at: lastDecision.decidedAt, pending: false }] : buildAuditTrail(signal)),
    [lastDecision, signal],
  )

  function selectTransition(target: WorkflowState) {
    setNextStep(nextStepForTarget(state, target))
  }

  function openSource(sourceId: string) {
    setSourceTab('todas')
    setExpandedIds((ids) => (ids.includes(sourceId) ? ids : [...ids, sourceId]))
    window.setTimeout(() => document.getElementById(`ficha-${sourceId}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' }), 0)
  }

  function toggleRemoved(sourceId: string) {
    setRemovedIds((ids) => (ids.includes(sourceId) ? ids.filter((id) => id !== sourceId) : [...ids, sourceId]))
  }

  function registerDecision() {
    const finalState = decision === 'rejeitar' ? 'encerrado' : resultingState
    const review: ReviewDecision = {
      id: 'demo-review',
      signalId: signal.id,
      type: decision,
      removedSourceIds: removedIds,
      comment: comment || undefined,
      nextStep: decision === 'rejeitar' ? 'encerrar' : nextStep,
      resultingState: finalState,
      decidedAt: '2026-10-07T14:32:00-04:00',
      decidedBy: 'Analista de vigilância (demonstração)',
    }
    setState(finalState)
    setLastDecision(review)
    toast.success('Decisão simulada registrada', {
      description: 'Nenhum dado foi enviado ou alterado fora deste mockup.',
    })
  }

  return (
    <div className="mx-auto flex w-full max-w-[1440px] flex-col gap-5 px-4 py-5 md:px-6 md:py-6 lg:px-8">
      <SignalHeader signal={signal} state={state} updatedAt={lastDecision?.decidedAt ?? signal.updatedAt} />
      <SignalStatusStepper current={state} onSelectTransition={selectTransition} />

      <div className="grid items-start gap-5 xl:grid-cols-[minmax(0,1fr)_360px]">
        <div className="flex min-w-0 flex-col gap-5">
          <SignalSummary signal={signal} sourceCounts={countSourcesByType(signal)} />
          <EvidenceThread
            signal={signal}
            sources={sources}
            removedIds={removedIds}
            lastDecision={lastDecision}
            onOpenSheet={openSource}
          />
          <GroupingCriteria criteria={signal.criteria} />
          <SourceSheets
            sources={sources}
            removedIds={removedIds}
            tab={sourceTab}
            onTabChange={setSourceTab}
            expandedIds={expandedIds}
            onExpandedChange={(id, open) => setExpandedIds((ids) => (open ? [...new Set([...ids, id])] : ids.filter((item) => item !== id)))}
          />
          <AuditTimeline events={auditTrail} />
        </div>

        <aside className="sticky top-[76px] flex flex-col gap-4 xl:max-h-[calc(100dvh-92px)] xl:overflow-y-auto xl:pr-1">
          <section aria-labelledby="decisao-titulo" className="rounded-md border border-encontro/25 bg-mineral">
            <div className="border-b border-agua px-4 py-3">
              <h2 id="decisao-titulo" className="text-base font-semibold text-encontro">Decisão do analista</h2>
              <p className="mt-1 text-sm text-ardosia">Revise as fontes antes de registrar uma ação.</p>
            </div>

            <div className="flex flex-col gap-4 p-4">
              <fieldset>
                <legend className="text-sm font-medium text-grafite">Sobre o agrupamento</legend>
                <div className="mt-2 grid gap-2">
                  {DECISION_OPTIONS.map(({ value, icon: Icon, description }) => {
                    const selected = decision === value
                    return (
                      <button
                        key={value}
                        type="button"
                        aria-pressed={selected}
                        onClick={() => setDecision(value)}
                        className={cn(
                          'flex min-h-12 items-start gap-2.5 rounded-sm border p-2.5 text-left transition-colors',
                          selected ? 'border-igarape bg-vitoria-soft/60' : 'border-agua hover:bg-nevoa',
                        )}
                      >
                        <span className={cn('mt-0.5 flex size-5 shrink-0 items-center justify-center rounded-full border', selected ? 'border-igarape bg-igarape text-mineral' : 'border-agua-strong text-transparent')}>
                          <Icon className="size-3" aria-hidden />
                        </span>
                        <span>
                          <span className="block text-sm font-medium text-encontro">{DECISION_LABEL[value]}</span>
                          <span className="block text-xs leading-relaxed text-ardosia">{description}</span>
                        </span>
                      </button>
                    )
                  })}
                </div>
              </fieldset>

              {decision === 'corrigir' && (
                <fieldset className="border-t border-agua pt-4">
                  <legend className="text-sm font-medium text-grafite">Evidências a retirar</legend>
                  <p className="mt-1 text-xs text-ardosia">A retirada é apenas uma simulação visual nesta versão.</p>
                  <div className="mt-2 grid gap-2">
                    {sources.map((source) => (
                      <label key={source.id} className="flex cursor-pointer gap-2 rounded-sm border border-agua px-2.5 py-2 text-sm hover:bg-nevoa">
                        <input
                          type="checkbox"
                          checked={removedIds.includes(source.id)}
                          onChange={() => toggleRemoved(source.id)}
                          className="mt-0.5 size-4 accent-igarape"
                        />
                        <span className="min-w-0"><span className="block truncate font-mono text-xs text-ardosia">{source.code}</span><span className="block text-grafite">{source.title}</span></span>
                      </label>
                    ))}
                  </div>
                </fieldset>
              )}

              <fieldset className="border-t border-agua pt-4">
                <legend className="text-sm font-medium text-grafite">Próximo passo</legend>
                <div className="mt-2 grid gap-2">
                  {(['manter', 'avancar', 'encerrar'] as const).map((option) => {
                    const disabled = option === 'avancar' && state === 'avaliacao_risco'
                    return (
                      <label key={option} className={cn('flex min-h-10 items-center gap-2 rounded-sm px-1 text-sm', disabled && 'cursor-not-allowed opacity-45')}>
                        <input
                          type="radio"
                          name="next-step"
                          value={option}
                          checked={nextStep === option}
                          disabled={disabled}
                          onChange={() => setNextStep(option)}
                          className="size-4 accent-igarape"
                        />
                        {nextStepLabel(state, option)}
                      </label>
                    )
                  })}
                </div>
                <div className="mt-2 flex items-center gap-2 rounded-sm bg-nevoa px-2.5 py-2 text-xs text-ardosia">
                  <CircleAlert className="size-4 shrink-0 text-andiroba-ink" aria-hidden />
                  Resultado: <StateLabel state={decision === 'rejeitar' ? 'encerrado' : resultingState} className="text-xs" />
                </div>
              </fieldset>

              <label className="block border-t border-agua pt-4 text-sm font-medium text-grafite">
                Comentário da revisão <span className="font-normal text-ardosia">(opcional)</span>
                <Textarea value={comment} onChange={(event) => setComment(event.target.value)} placeholder="Registre o motivo ou a orientação para a próxima etapa." className="mt-2 min-h-24 bg-mineral" />
              </label>

              <Button className="h-11 w-full" onClick={registerDecision}>
                <SendHorizontal aria-hidden />
                Registrar decisão simulada
              </Button>
              <p className="text-xs leading-relaxed text-ardosia">A prioridade e a correlação são sugestões auditáveis. A decisão sanitária permanece humana.</p>
            </div>
          </section>
        </aside>
      </div>
    </div>
  )
}
