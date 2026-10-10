'use client'

import { ChevronUp, ChevronsUp, Info, MessagesSquare, Minus, Newspaper } from 'lucide-react'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { PRIORITY_DESCRIPTION, PRIORITY_LABEL, SOURCE_TYPE_LABEL, WORKFLOW_QUEUE_LABEL } from '@/lib/labels'
import type { SourceType, SuggestedPriority, WorkflowState } from '@/lib/types'
import { cn } from '@/lib/utils'

const PRIORITY_STYLE: Record<SuggestedPriority, string> = {
  urgente: 'bg-urucum-soft text-urucum-ink border-urucum/40',
  atencao: 'bg-andiroba-soft text-andiroba-ink border-andiroba/50',
  monitorar: 'bg-vitoria-soft text-igarape-ink border-vitoria',
  contexto: 'bg-muted text-ardosia border-agua-strong',
}

const PRIORITY_ICON: Record<SuggestedPriority, typeof ChevronUp> = {
  urgente: ChevronsUp,
  atencao: ChevronUp,
  monitorar: Minus,
  contexto: Info,
}

export function PriorityBadge({
  priority,
  showSuggested = true,
  withTooltip = true,
  className,
}: {
  priority: SuggestedPriority | null
  showSuggested?: boolean
  withTooltip?: boolean
  className?: string
}) {
  if (priority === null) {
    return (
      <span className={cn('inline-flex h-6 items-center rounded-sm border border-agua-strong px-1.5 text-xs text-ardosia', className)}>
        Sem sugestão
      </span>
    )
  }
  const Icon = PRIORITY_ICON[priority]
  const content = (
    <>
      <Icon className="size-3.5" aria-hidden />
      <span className="font-semibold">{PRIORITY_LABEL[priority]}</span>
      {showSuggested && <span className="font-normal opacity-80">· sugerida</span>}
    </>
  )
  const base = cn(
    'inline-flex h-6 items-center gap-1 rounded-sm border px-1.5 text-xs whitespace-nowrap',
    PRIORITY_STYLE[priority],
    className,
  )

  if (!withTooltip) return <span className={base}>{content}</span>

  return (
    <Tooltip>
      <TooltipTrigger
        className={cn(base, 'cursor-help')}
        aria-label={`Prioridade sugerida: ${PRIORITY_LABEL[priority]}. ${PRIORITY_DESCRIPTION[priority]}`}
      >
        {content}
      </TooltipTrigger>
      <TooltipContent className="max-w-64 text-pretty">
        <p className="font-semibold">Prioridade sugerida pelo sistema</p>
        <p className="mt-0.5">{PRIORITY_DESCRIPTION[priority]}</p>
        <p className="mt-1 opacity-80">A prioridade final é definida pela vigilância.</p>
      </TooltipContent>
    </Tooltip>
  )
}

const STATE_STROKE: Record<WorkflowState, string> = {
  detectado: '#52656C',
  triagem: '#B08A1F',
  verificacao: '#14736F',
  avaliacao_risco: '#C85C43',
  encerrado: '#7F9299',
}

export function StateGlyph({ state, size = 12 }: { state: WorkflowState; size?: number }) {
  const stroke = STATE_STROKE[state]
  return (
    <svg width={size} height={size} viewBox="0 0 12 12" aria-hidden className="shrink-0">
      {state === 'detectado' && <circle cx="6" cy="6" r="4.5" fill="none" stroke={stroke} strokeWidth="1.5" strokeDasharray="1 1.8" />}
      {state === 'triagem' && <circle cx="6" cy="6" r="4.5" fill="none" stroke={stroke} strokeWidth="2" />}
      {state === 'verificacao' && <circle cx="6" cy="6" r="4.5" fill="none" stroke={stroke} strokeWidth="2" strokeDasharray="3 1.6" />}
      {state === 'avaliacao_risco' && (
        <>
          <circle cx="6" cy="6" r="5" fill="none" stroke={stroke} strokeWidth="1.2" />
          <circle cx="6" cy="6" r="2.4" fill={stroke} />
        </>
      )}
      {state === 'encerrado' && <circle cx="6" cy="6" r="4.5" fill={stroke} />}
    </svg>
  )
}

export function StateLabel({ state, className }: { state: WorkflowState; className?: string }) {
  return (
    <span className={cn('inline-flex items-center gap-1.5 text-sm text-grafite whitespace-nowrap', className)}>
      <StateGlyph state={state} />
      {WORKFLOW_QUEUE_LABEL[state]}
    </span>
  )
}

export function SourceTypeIcon({ type, className }: { type: SourceType; className?: string }) {
  const Icon = type === 'midia' ? Newspaper : MessagesSquare
  return <Icon className={cn('size-4', className)} aria-label={SOURCE_TYPE_LABEL[type]} role="img" />
}

export function SourceCounts({ media, community }: { media: number; community: number }) {
  return (
    <span className="inline-flex items-center gap-3 text-sm text-grafite">
      <span className="inline-flex items-center gap-1" title="Fontes de mídia">
        <Newspaper className="size-4 text-encontro" aria-hidden />
        <span>{media}</span>
        <span className="sr-only">de mídia</span>
      </span>
      <span className="inline-flex items-center gap-1" title="Fontes comunitárias">
        <MessagesSquare className="size-4 text-igarape" aria-hidden />
        <span>{community}</span>
        <span className="sr-only">comunitárias</span>
      </span>
    </span>
  )
}
