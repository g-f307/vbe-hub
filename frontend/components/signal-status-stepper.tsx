'use client'

import { Check } from 'lucide-react'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { StateGlyph } from '@/components/status-badges'
import { VALID_TRANSITIONS, WORKFLOW_LABEL, WORKFLOW_ORDER } from '@/lib/labels'
import type { WorkflowState } from '@/lib/types'
import { cn } from '@/lib/utils'

type StepStatus = 'done' | 'current' | 'available' | 'blocked'

function stepStatus(step: WorkflowState, current: WorkflowState): StepStatus {
  const stepIndex = WORKFLOW_ORDER.indexOf(step)
  const currentIndex = WORKFLOW_ORDER.indexOf(current)
  if (step === current) return 'current'
  if (current === 'encerrado') return 'blocked'
  if (stepIndex < currentIndex) return 'done'
  if (VALID_TRANSITIONS[current].includes(step)) return 'available'
  return 'blocked'
}

function hint(status: StepStatus, step: WorkflowState, current: WorkflowState) {
  if (status === 'current') return 'Etapa atual do sinal.'
  if (status === 'done') return 'Etapa já concluída.'
  if (status === 'available') return `Transição permitida. Clique para selecionar como próxima etapa no painel de decisão.`
  return `Transição não permitida a partir de ${WORKFLOW_LABEL[current].toLowerCase()}.`
}

export function SignalStatusStepper({
  current,
  onSelectTransition,
}: {
  current: WorkflowState
  onSelectTransition: (target: WorkflowState) => void
}) {
  const currentIndex = WORKFLOW_ORDER.indexOf(current)

  return (
    <nav aria-label="Etapas do fluxo de vigilância" className="rounded-md border border-agua bg-mineral px-3 py-3 md:px-4">
      <p className="mb-2 flex items-baseline justify-between text-xs text-ardosia md:hidden">
        <span>
          Etapa {currentIndex + 1} de {WORKFLOW_ORDER.length}
        </span>
        <span className="font-semibold text-encontro">{WORKFLOW_LABEL[current]}</span>
      </p>
      <ol className="flex items-center gap-1 md:gap-0">
        {WORKFLOW_ORDER.map((step, index) => {
          const status = stepStatus(step, current)
          const interactive = status === 'available'
          return (
            <li key={step} className="flex min-w-0 flex-1 items-center">
              <Tooltip>
                <TooltipTrigger
                  render={
                    <button
                      type="button"
                      aria-current={status === 'current' ? 'step' : undefined}
                      aria-disabled={!interactive}
                      onClick={() => interactive && onSelectTransition(step)}
                      className={cn(
                        'group flex min-h-11 w-full min-w-0 flex-col items-stretch gap-1.5 rounded-sm px-1 py-1 text-left md:flex-row md:items-center md:gap-2 md:px-2',
                        interactive ? 'cursor-pointer hover:bg-vitoria-soft' : 'cursor-default',
                      )}
                    />
                  }
                >
                  <span
                    className={cn(
                      'h-1.5 w-full rounded-full md:hidden',
                      status === 'done' && 'bg-igarape',
                      status === 'current' && 'bg-encontro',
                      status === 'available' && 'bg-vitoria',
                      status === 'blocked' && 'bg-agua',
                    )}
                    aria-hidden
                  />
                  <span
                    className={cn(
                      'hidden size-7 shrink-0 items-center justify-center rounded-full border md:flex',
                      status === 'done' && 'border-igarape bg-igarape text-mineral',
                      status === 'current' && 'border-encontro bg-encontro text-mineral',
                      status === 'available' && 'border-dashed border-igarape bg-mineral group-hover:bg-vitoria-soft',
                      status === 'blocked' && 'border-agua-strong bg-muted',
                    )}
                    aria-hidden
                  >
                    {status === 'done' ? (
                      <Check className="size-3.5" />
                    ) : status === 'current' ? (
                      <span className="text-[11px] font-semibold">{index + 1}</span>
                    ) : (
                      <StateGlyph state={step} size={11} />
                    )}
                  </span>
                  <span
                    className={cn(
                      'sr-only truncate text-sm md:not-sr-only',
                      status === 'current' && 'font-semibold text-encontro',
                      status === 'done' && 'text-grafite',
                      status === 'available' && 'font-medium text-igarape-ink underline-offset-4 group-hover:underline',
                      status === 'blocked' && 'text-ardosia/80',
                    )}
                  >
                    {WORKFLOW_LABEL[step]}
                    <span className="sr-only">. {hint(status, step, current)}</span>
                  </span>
                </TooltipTrigger>
                <TooltipContent className="max-w-60 text-pretty">{hint(status, step, current)}</TooltipContent>
              </Tooltip>
              {index < WORKFLOW_ORDER.length - 1 && (
                <span
                  className={cn(
                    'mx-1 hidden h-px min-w-3 flex-1 md:block',
                    index < currentIndex ? 'bg-igarape' : 'bg-agua-strong',
                  )}
                  aria-hidden
                />
              )}
            </li>
          )
        })}
      </ol>
    </nav>
  )
}
