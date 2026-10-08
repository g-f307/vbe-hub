'use client'

import { FileSearch, Megaphone, MessagesSquare, Newspaper, UserCheck } from 'lucide-react'
import { VbeMark } from '@/components/vbe-logo'
import { formatDateTime } from '@/lib/format'
import { RELATION_LABEL, WORKFLOW_LABEL } from '@/lib/labels'
import { DECISION_PAST_LABEL } from '@/lib/review'
import type { RelationKind, ReviewDecision, Signal, SourceRecord } from '@/lib/types'
import { cn } from '@/lib/utils'

const RELATION_STYLE: Record<RelationKind, { text: string; bar: string }> = {
  corroboracao: { text: 'text-igarape-ink', bar: 'bg-igarape' },
  atualizacao: { text: 'text-encontro', bar: 'bg-encontro' },
  contexto: { text: 'text-ardosia', bar: 'bg-ardosia' },
  divergencia: { text: 'text-urucum-ink', bar: 'bg-urucum' },
}

export function EvidenceThread({
  signal,
  sources,
  removedIds,
  lastDecision,
  onOpenSheet,
}: {
  signal: Signal
  sources: SourceRecord[]
  removedIds: string[]
  lastDecision?: ReviewDecision
  onOpenSheet: (sourceId: string) => void
}) {
  const activeCount = sources.filter((s) => !removedIds.includes(s.id)).length

  return (
    <section aria-labelledby="linha-titulo" className="rounded-md border border-agua bg-mineral px-4 py-4 md:px-5">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 id="linha-titulo" className="text-base font-semibold text-encontro">
          Linha de evidências
        </h2>
        <p className="text-sm text-ardosia">
          {activeCount} registros vinculados · relações sugeridas pelo sistema
        </p>
      </div>

      <ol className="mt-4">
        {sources.map((source) => (
          <EvidenceNode
            key={source.id}
            source={source}
            removed={removedIds.includes(source.id)}
            onOpenSheet={() => onOpenSheet(source.id)}
          />
        ))}

        <li className="relative flex gap-3">
          <Rail kind="solid">
            <span className="flex size-9 items-center justify-center rounded-md bg-encontro text-vitoria">
              <VbeMark className="size-5" />
            </span>
          </Rail>
          <div className="mb-5 min-w-0 flex-1 rounded-md border border-encontro/25 bg-vitoria-soft/60 px-3 py-3">
            <p className="text-xs font-medium tracking-wide text-igarape-ink uppercase">Sinal consolidado</p>
            <p className="mt-0.5 text-sm font-semibold text-encontro">
              <span className="font-mono text-xs font-normal text-ardosia">{signal.code}</span> · {signal.title}
            </p>
            <p className="mt-1 text-sm text-pretty text-grafite">
              {activeCount} registros, {signal.neighborhood}. {signal.symptoms.join(', ')}.
            </p>
          </div>
        </li>

        <li className="relative flex gap-3">
          <Rail kind="end">
            <span
              className={cn(
                'flex size-9 items-center justify-center rounded-full',
                lastDecision ? 'bg-igarape text-mineral' : 'border-2 border-dashed border-agua-strong bg-mineral text-ardosia',
              )}
            >
              <UserCheck className="size-4" aria-hidden />
            </span>
          </Rail>
          <div
            className={cn(
              'min-w-0 flex-1 rounded-md px-3 py-3',
              lastDecision ? 'border border-igarape/40 bg-mineral' : 'border border-dashed border-agua-strong',
            )}
          >
            {lastDecision ? (
              <>
                <p className="text-xs font-medium tracking-wide text-igarape-ink uppercase">Decisão registrada</p>
                <p className="mt-0.5 text-sm font-semibold text-encontro">
                  {DECISION_PAST_LABEL[lastDecision.type]} · {WORKFLOW_LABEL[lastDecision.resultingState]}
                </p>
                <p className="mt-0.5 text-sm text-ardosia">
                  {lastDecision.decidedBy} · <time dateTime={lastDecision.decidedAt}>{formatDateTime(lastDecision.decidedAt)}</time>
                </p>
              </>
            ) : (
              <>
                <p className="text-xs font-medium tracking-wide text-ardosia uppercase">Decisão do analista</p>
                <p className="mt-0.5 text-sm text-grafite">Nenhuma decisão humana está registrada nesta leitura.</p>
              </>
            )}
          </div>
        </li>
      </ol>
    </section>
  )
}

function EvidenceNode({
  source,
  removed,
  onOpenSheet,
}: {
  source: SourceRecord
  removed: boolean
  onOpenSheet: () => void
}) {
  const Icon = source.isContext ? Megaphone : source.type === 'midia' ? Newspaper : MessagesSquare
  const relation = source.relation ? RELATION_STYLE[source.relation.kind] : null
  const confidence = source.relation ? Math.round(source.relation.confidence * 100) : null

  return (
    <li className="relative flex gap-3">
      <Rail kind={source.isContext || removed ? 'dashed' : 'solid'}>
        <span
          className={cn(
            'flex size-9 items-center justify-center rounded-full border',
            removed && 'border-dashed border-agua-strong bg-muted text-ardosia/70',
            !removed && source.isContext && 'border-dashed border-ardosia bg-mineral text-ardosia',
            !removed && !source.isContext && source.type === 'midia' && 'border-encontro/30 bg-encontro text-mineral',
            !removed && !source.isContext && source.type === 'comunidade' && 'border-igarape/30 bg-igarape text-mineral',
          )}
        >
          <Icon className="size-4" aria-hidden />
        </span>
      </Rail>

      <article
        aria-label={`${source.subtype}: ${source.title}`}
        className={cn(
          'mb-5 min-w-0 flex-1 rounded-md border px-3 py-3',
          removed && 'border-dashed border-agua-strong bg-muted/60',
          !removed && source.isContext && 'border-dashed border-agua-strong bg-mineral',
          !removed && !source.isContext && 'border-agua bg-mineral',
        )}
      >
        <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-ardosia">
          <span className="font-semibold tracking-wide text-grafite uppercase">{source.subtype}</span>
          <span aria-hidden>·</span>
          <time dateTime={source.publishedAt}>{formatDateTime(source.publishedAt)}</time>
          <span aria-hidden>·</span>
          <span>{source.neighborhood}</span>
          {source.isContext && (
            <span className="rounded-sm border border-agua-strong px-1 py-px text-[11px] text-ardosia">Contexto</span>
          )}
          {removed && (
            <span className="rounded-sm bg-urucum-soft px-1 py-px text-[11px] font-medium text-urucum-ink">
              Removido do sinal
            </span>
          )}
        </div>
        <h3 className={cn('mt-1 text-sm font-semibold text-pretty text-encontro', removed && 'text-ardosia line-through')}>
          {source.title}
        </h3>
        <p className={cn('mt-1 text-sm text-pretty text-grafite', removed && 'text-ardosia')}>{source.excerpt}</p>

        <div className="mt-2.5 flex flex-col gap-2 border-t border-agua pt-2.5 sm:flex-row sm:items-center sm:justify-between">
          <div className="min-w-0">
            {source.relation && relation && confidence !== null ? <>
              <p className={cn('text-xs font-semibold', relation.text)}>
                {RELATION_LABEL[source.relation.kind]}
                <span className="font-normal text-ardosia"> · confiança {confidence}%</span>
              </p>
              <div className="mt-1 flex items-center gap-2">
                <span className="h-1 w-24 overflow-hidden rounded-full bg-agua" aria-hidden><span className={cn('block h-full rounded-full', relation.bar)} style={{ width: `${confidence}%` }} /></span>
                <span className="truncate text-xs text-ardosia">{source.relation.rationale}</span>
              </div>
            </> : <p className="text-xs text-ardosia">Relação disponível nos critérios de agrupamento.</p>}
          </div>
          <button
            type="button"
            onClick={onOpenSheet}
            className="inline-flex min-h-11 shrink-0 items-center gap-1.5 self-start rounded-sm px-2 text-sm font-medium text-igarape-ink hover:bg-vitoria-soft sm:min-h-8 sm:self-auto"
          >
            <FileSearch className="size-4" aria-hidden />
            Ver ficha
            <span className="sr-only"> técnica de {source.code}</span>
          </button>
        </div>
      </article>
    </li>
  )
}

function Rail({ kind, children }: { kind: 'solid' | 'dashed' | 'end'; children: React.ReactNode }) {
  return (
    <div className="relative flex w-9 shrink-0 justify-center" aria-hidden>
      {kind !== 'end' && (
        <span
          className={cn(
            'absolute top-9 bottom-0 left-1/2 -translate-x-1/2',
            kind === 'solid' ? 'w-0.5 bg-igarape/50' : 'border-l-2 border-dashed border-agua-strong',
          )}
        />
      )}
      <span className="relative z-10">{children}</span>
    </div>
  )
}
