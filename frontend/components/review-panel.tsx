'use client'

import { useState } from 'react'
import { CheckCircle2, CircleAlert, RefreshCw, Send, ShieldCheck } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { formatDateTime } from '@/lib/format'
import { VALID_TRANSITIONS, WORKFLOW_LABEL } from '@/lib/labels'
import type { ReviewTarget } from '@/lib/signal-read'
import type { WorkflowState } from '@/lib/types'
import {
  WorkflowActionError,
  createOperationKey,
  submitReview,
  submitTransition,
  type ReviewAction,
  type WorkflowOutcome,
} from '@/lib/workflow-client'
import { cn } from '@/lib/utils'

type WorkflowView = { state: WorkflowState; version: number; updatedAt: string | null }
type PendingAction = { kind: 'review' | 'transition'; title: string; description: string }

const UI_TO_API_STATE = {
  detectado: 'detected',
  triagem: 'triage',
  verificacao: 'verification',
  avaliacao_risco: 'risk_assessment',
  encerrado: 'closed',
} as const

const REVIEW_ACTIONS: Array<{ value: ReviewAction; label: string; detail: string }> = [
  { value: 'accept', label: 'Aceitar', detail: 'Mantém a sugestão como está.' },
  { value: 'correct', label: 'Corrigir', detail: 'Registra um ajuste proposto.' },
  { value: 'reject', label: 'Rejeitar', detail: 'Descarta a sugestão com justificativa.' },
]

const REVIEW_REASONS = [
  { value: 'different_event', label: 'Trata-se de evento diferente' },
  { value: 'insufficient_evidence', label: 'Evidência insuficiente' },
  { value: 'local_context', label: 'Contexto local altera a leitura' },
  { value: 'other', label: 'Outro motivo' },
]

const CLOSURE_REASONS = [
  { value: 'duplicate', label: 'Registro duplicado' },
  { value: 'insufficient_evidence', label: 'Evidência insuficiente' },
  { value: 'not_public_health_event', label: 'Não caracteriza evento de saúde pública' },
  { value: 'resolved', label: 'Sinal resolvido' },
  { value: 'other', label: 'Outro motivo' },
]

export function ReviewPanel({
  signalId,
  workflow,
  targets,
  onOutcome,
  onReload,
}: {
  signalId: string
  workflow: WorkflowView
  targets: ReviewTarget[]
  onOutcome: (outcome: WorkflowOutcome) => void
  onReload: () => void
}) {
  const [targetId, setTargetId] = useState(targets[0]?.id ?? '')
  const [action, setAction] = useState<ReviewAction>('accept')
  const [reasonCode, setReasonCode] = useState('')
  const [comment, setComment] = useState('')
  const [correctionField, setCorrectionField] = useState('')
  const [correctionValue, setCorrectionValue] = useState('')
  const [targetState, setTargetState] = useState<WorkflowState | ''>('')
  const [closureReason, setClosureReason] = useState('')
  const [pending, setPending] = useState<PendingAction | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [message, setMessage] = useState<{ tone: 'error' | 'success'; text: string; conflict?: boolean } | null>(null)

  const selectedTarget = targets.find((target) => target.id === targetId) ?? targets[0]
  const availableTransitions = VALID_TRANSITIONS[workflow.state]

  function prepareReview() {
    setMessage(null)
    if (!selectedTarget) return setMessage({ tone: 'error', text: 'Não há sugestão disponível para revisão neste sinal.' })
    if ((action === 'correct' || action === 'reject') && !reasonCode) {
      return setMessage({ tone: 'error', text: 'Selecione o motivo estruturado da decisão.' })
    }
    if (action === 'correct' && (!correctionField.trim() || !correctionValue.trim())) {
      return setMessage({ tone: 'error', text: 'Informe o campo e o valor propostos para a correção.' })
    }
    setPending({
      kind: 'review',
      title: 'Confirmar decisão sobre sugestão?',
      description: `${action === 'accept' ? 'Aceitará' : action === 'correct' ? 'Registrará uma correção para' : 'Rejeitará'} “${selectedTarget.label}”. A decisão será registrada no histórico auditável.`,
    })
  }

  function prepareTransition() {
    setMessage(null)
    if (!targetState) return setMessage({ tone: 'error', text: 'Selecione a próxima etapa do fluxo.' })
    if (targetState === 'encerrado' && !closureReason) {
      return setMessage({ tone: 'error', text: 'Selecione o motivo estruturado para encerrar o sinal.' })
    }
    setPending({
      kind: 'transition',
      title: 'Confirmar atualização do fluxo?',
      description: `O sinal seguirá para “${WORKFLOW_LABEL[targetState]}”. Esta atualização não confirma doença, surto ou medida sanitária.`,
    })
  }

  async function confirmAction() {
    if (!pending) return
    setIsSubmitting(true)
    setMessage(null)
    try {
      const outcome = pending.kind === 'review'
        ? await submitReview(signalId, {
            operationKey: createOperationKey('review'),
            expectedVersion: workflow.version,
            targetType: selectedTarget!.type,
            targetId: selectedTarget!.id,
            suggestionIdentityKey: selectedTarget!.suggestionIdentityKey,
            action,
            correctedValue: action === 'correct' ? { [correctionField.trim()]: correctionValue.trim() } : undefined,
            reasonCode: action === 'accept' ? undefined : reasonCode,
            comment: comment.trim() || undefined,
          })
        : await submitTransition(signalId, {
            operationKey: createOperationKey('transition'),
            expectedVersion: workflow.version,
            targetState: UI_TO_API_STATE[targetState as WorkflowState],
            reasonCode: targetState === 'encerrado' ? closureReason : undefined,
            comment: comment.trim() || undefined,
          })
      onOutcome(outcome)
      setPending(null)
      setMessage({ tone: 'success', text: 'Ação registrada. A versão e o histórico foram atualizados.' })
      setComment('')
      if (pending.kind === 'transition') {
        setTargetState('')
        setClosureReason('')
      }
    } catch (error) {
      const workflowError = error instanceof WorkflowActionError
        ? error
        : new WorkflowActionError('Não foi possível registrar a ação agora. Tente novamente.', 'unavailable')
      setPending(null)
      setMessage({ tone: 'error', text: workflowError.message, conflict: workflowError.kind === 'conflict' })
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <section aria-labelledby="decisao-titulo" className="rounded-md border border-encontro/25 bg-mineral">
      <div className="border-b border-agua px-4 py-3">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 id="decisao-titulo" className="text-base font-semibold text-encontro">Decisão do analista</h2>
            <p className="mt-1 text-sm text-ardosia">Registre uma revisão explícita; a sugestão automática não decide sozinha.</p>
          </div>
          <span className="rounded-sm bg-vitoria-soft px-2 py-1 font-mono text-xs text-igarape-ink">v{workflow.version}</span>
        </div>
        <p className="mt-2 text-xs text-ardosia">
          {workflow.updatedAt ? <>Atualizado em {formatDateTime(workflow.updatedAt)}</> : 'Ainda não há ação registrada para este sinal.'}
        </p>
      </div>

      <div className="flex flex-col gap-5 p-4">
        {message && (
          <div role="status" className={cn('flex gap-2 rounded-sm px-3 py-2.5 text-sm leading-relaxed', message.tone === 'error' ? 'bg-alerta-soft text-grafite' : 'bg-vitoria-soft text-grafite')}>
            {message.tone === 'error' ? <CircleAlert className="mt-0.5 size-4 shrink-0 text-andiroba-ink" aria-hidden /> : <CheckCircle2 className="mt-0.5 size-4 shrink-0 text-igarape-ink" aria-hidden />}
            <div className="min-w-0 flex-1">
              <p>{message.text}</p>
              {message.conflict && <Button type="button" variant="link" size="sm" className="mt-1 h-auto px-0" onClick={onReload}><RefreshCw /> Recarregar dados canônicos</Button>}
            </div>
          </div>
        )}

        <fieldset className="flex flex-col gap-2">
          <legend className="text-sm font-semibold text-grafite">Revisar sugestão</legend>
          <label className="text-xs font-medium text-ardosia" htmlFor="review-target">Alvo da revisão</label>
          <select id="review-target" value={selectedTarget?.id ?? ''} onChange={(event) => setTargetId(event.target.value)} disabled={isSubmitting} className="h-9 w-full rounded-md border border-agua-strong bg-mineral px-2.5 text-sm text-grafite focus:outline-none focus:ring-2 focus:ring-igarape/30">
            {targets.map((target) => <option key={`${target.type}-${target.id}`} value={target.id}>{target.label}</option>)}
          </select>
          <div className="mt-1 grid grid-cols-3 gap-1.5" role="radiogroup" aria-label="Decisão sobre sugestão">
            {REVIEW_ACTIONS.map((item) => (
              <button key={item.value} type="button" role="radio" aria-checked={action === item.value} disabled={isSubmitting} onClick={() => setAction(item.value)} className={cn('rounded-sm border px-2 py-2 text-left transition-colors', action === item.value ? 'border-igarape bg-vitoria-soft text-igarape-ink' : 'border-agua bg-mineral text-ardosia hover:bg-nevoa')}>
                <span className="block text-xs font-semibold">{item.label}</span>
                <span className="mt-0.5 block text-[11px] leading-snug">{item.detail}</span>
              </button>
            ))}
          </div>
          {(action === 'correct' || action === 'reject') && (
            <label className="mt-1 flex flex-col gap-1 text-xs font-medium text-ardosia">Motivo estruturado
              <select value={reasonCode} onChange={(event) => setReasonCode(event.target.value)} disabled={isSubmitting} className="h-9 rounded-md border border-agua-strong bg-mineral px-2.5 text-sm font-normal text-grafite focus:outline-none focus:ring-2 focus:ring-igarape/30">
                <option value="">Selecione o motivo</option>
                {REVIEW_REASONS.map((reason) => <option key={reason.value} value={reason.value}>{reason.label}</option>)}
              </select>
            </label>
          )}
          {action === 'correct' && (
            <div className="grid gap-2 sm:grid-cols-2">
              <label className="flex flex-col gap-1 text-xs font-medium text-ardosia">Campo a corrigir<Input value={correctionField} onChange={(event) => setCorrectionField(event.target.value)} placeholder="ex.: condition" disabled={isSubmitting} /></label>
              <label className="flex flex-col gap-1 text-xs font-medium text-ardosia">Valor proposto<Input value={correctionValue} onChange={(event) => setCorrectionValue(event.target.value)} placeholder="Descreva o ajuste" disabled={isSubmitting} /></label>
            </div>
          )}
          <Button type="button" variant="outline" className="mt-1 w-full" disabled={isSubmitting || !selectedTarget} onClick={prepareReview}><ShieldCheck /> Revisar sugestão</Button>
        </fieldset>

        <fieldset className="flex flex-col gap-2 border-t border-agua pt-4">
          <legend className="text-sm font-semibold text-grafite">Atualizar fluxo</legend>
          {availableTransitions.length ? (
            <>
              <div className="grid gap-1.5">
                {availableTransitions.map((state) => <label key={state} className={cn('flex cursor-pointer items-center gap-2 rounded-sm border px-2.5 py-2 text-sm', targetState === state ? 'border-igarape bg-vitoria-soft text-igarape-ink' : 'border-agua text-ardosia')}><input type="radio" name="target-state" value={state} checked={targetState === state} onChange={() => setTargetState(state)} disabled={isSubmitting} />{WORKFLOW_LABEL[state]}</label>)}
              </div>
              {targetState === 'encerrado' && <label className="flex flex-col gap-1 text-xs font-medium text-ardosia">Motivo do encerramento<select value={closureReason} onChange={(event) => setClosureReason(event.target.value)} disabled={isSubmitting} className="h-9 rounded-md border border-agua-strong bg-mineral px-2.5 text-sm font-normal text-grafite focus:outline-none focus:ring-2 focus:ring-igarape/30"><option value="">Selecione o motivo</option>{CLOSURE_REASONS.map((reason) => <option key={reason.value} value={reason.value}>{reason.label}</option>)}</select></label>}
              <Button type="button" className="mt-1 w-full" disabled={isSubmitting || !targetState} onClick={prepareTransition}><Send /> Atualizar fluxo</Button>
            </>
          ) : <p className="rounded-sm bg-nevoa px-3 py-2 text-sm text-ardosia">Este sinal está encerrado e não possui nova transição permitida.</p>}
        </fieldset>

        <label className="flex flex-col gap-1 border-t border-agua pt-4 text-xs font-medium text-ardosia">Comentário opcional para a ação selecionada<Textarea value={comment} onChange={(event) => setComment(event.target.value)} maxLength={500} placeholder="Contexto que ajude outra pessoa a entender esta decisão" disabled={isSubmitting} /></label>
        <div className="flex gap-2 rounded-sm bg-nevoa px-3 py-2.5 text-xs leading-relaxed text-ardosia"><CircleAlert className="mt-0.5 size-4 shrink-0 text-andiroba-ink" aria-hidden />Prioridade, extração e correlação são sugestões auditáveis; não confirmam doença, surto ou decisão sanitária.</div>
      </div>

      <Dialog open={pending !== null} onOpenChange={(open) => !open && !isSubmitting && setPending(null)}>
        <DialogContent showCloseButton={!isSubmitting}>
          <DialogHeader><DialogTitle>{pending?.title}</DialogTitle><DialogDescription>{pending?.description}</DialogDescription></DialogHeader>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setPending(null)} disabled={isSubmitting}>Voltar</Button>
            <Button type="button" onClick={confirmAction} disabled={isSubmitting}>{isSubmitting ? 'Registrando…' : 'Confirmar registro'}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </section>
  )
}
