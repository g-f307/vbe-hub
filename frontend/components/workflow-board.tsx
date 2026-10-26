import Link from 'next/link'
import { ArrowRight, Columns3, List, MapPin, ShieldCheck } from 'lucide-react'

import { PriorityBadge, SourceCounts, StateGlyph } from '@/components/status-badges'
import { formatPeriod } from '@/lib/format'
import { WORKFLOW_ORDER } from '@/lib/labels'
import type { Signal, WorkflowState } from '@/lib/types'
import { cn } from '@/lib/utils'

const COLUMN_META: Record<WorkflowState, { title: string; description: string; accent: string }> = {
  detectado: { title: 'Detectados', description: 'Entrada ainda não triada', accent: 'border-t-ardosia' },
  triagem: { title: 'Em triagem', description: 'Aguardam revisão inicial', accent: 'border-t-andiroba' },
  verificacao: { title: 'Em verificação', description: 'Evidências sob conferência', accent: 'border-t-igarape' },
  avaliacao_risco: { title: 'Avaliação de risco', description: 'Impacto em análise', accent: 'border-t-urucum' },
  encerrado: { title: 'Encerrados', description: 'Fluxo concluído', accent: 'border-t-agua-strong' },
}

export function WorkflowBoard({
  signals,
  total,
  view,
  queryString,
  limit = 100,
}: {
  signals: Signal[]
  total: number
  view: 'board' | 'list'
  queryString: string
  limit?: number
}) {
  const grouped = groupSignals(signals)
  const boardHref = boardViewHref(queryString, 'board')
  const listHref = boardViewHref(queryString, 'list')
  const triageHref = `/triagem${queryString ? `?${queryString}` : ''}`

  return (
    <section aria-labelledby="fluxo-title" className="flex flex-col gap-4">
      <div className="flex flex-col gap-3 border-y border-agua bg-mineral px-3 py-3 sm:flex-row sm:items-center sm:justify-between sm:rounded-md sm:border">
        <div>
          <h2 id="fluxo-title" className="text-sm font-semibold text-encontro">Fluxo dos sinais</h2>
          <p className="mt-0.5 text-xs text-ardosia">
            {signals.length} {signals.length === 1 ? 'sinal exibido' : 'sinais exibidos'} de {total} {total === 1 ? 'encontrado' : 'encontrados'}. A decisão final é da vigilância.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <div className="inline-flex rounded-md border border-agua bg-nevoa p-0.5" aria-label="Modo de visualização">
            <ViewLink href={boardHref} active={view === 'board'}><Columns3 aria-hidden />Quadro</ViewLink>
            <ViewLink href={listHref} active={view === 'list'}><List aria-hidden />Lista acessível</ViewLink>
          </div>
          <Link href={triageHref} className="inline-flex h-9 items-center rounded-md px-3 text-sm font-medium text-igarape hover:bg-vitoria-soft">
            Abrir fila de triagem
          </Link>
        </div>
      </div>

      {total > limit ? (
        <p role="status" className="rounded-md border border-andiroba/50 bg-andiroba-soft px-3 py-2 text-sm text-andiroba-ink">
          A visão está limitada aos {limit} primeiros de {total} sinais. Use os filtros ou a fila de triagem para reduzir a consulta.
        </p>
      ) : null}

      {view === 'list' ? <WorkflowTable signals={signals} /> : (
        <div className="grid gap-3 lg:grid-cols-5" aria-label="Quadro do fluxo canônico">
          {WORKFLOW_ORDER.map((state) => {
            const meta = COLUMN_META[state]
            const items = grouped[state]
            return (
              <section key={state} aria-labelledby={`coluna-${state}`} className={cn('min-w-0 rounded-md border border-t-[3px] border-agua bg-nevoa/55', meta.accent)}>
                <div className="flex min-h-16 items-start justify-between gap-2 border-b border-agua px-3 py-2.5">
                  <div>
                    <h3 id={`coluna-${state}`} className="flex items-center gap-1.5 text-sm font-semibold text-encontro"><StateGlyph state={state} />{meta.title}</h3>
                    <p className="mt-1 text-[11px] leading-snug text-ardosia">{meta.description}</p>
                  </div>
                  <span className="flex min-w-6 items-center justify-center rounded-sm bg-mineral px-1.5 py-0.5 font-mono text-xs text-ardosia">{items.length}</span>
                </div>
                {items.length ? (
                  <ol className="flex flex-col gap-2 p-2">
                    {items.map((signal) => <li key={signal.id}><WorkflowCard signal={signal} /></li>)}
                  </ol>
                ) : (
                  <p className="px-3 py-8 text-center text-xs leading-relaxed text-ardosia">Nenhum sinal neste estágio com os filtros atuais.</p>
                )}
              </section>
            )
          })}
        </div>
      )}
    </section>
  )
}

function WorkflowCard({ signal }: { signal: Signal }) {
  const counts = signal.sourceCounts ?? { midia: 0, comunidade: 0, total: 0 }
  return (
    <article className="group rounded-md border border-agua bg-mineral p-3 shadow-[0_1px_2px_rgba(16,47,60,0.04)] focus-within:border-igarape">
      <div className="flex items-start justify-between gap-2">
        <span className="min-w-0 truncate font-mono text-[11px] text-ardosia" title={signal.code}>{signal.code}</span>
        <PriorityBadge priority={signal.priority} showSuggested={false} withTooltip={false} className="shrink-0" />
      </div>
      <span className="sr-only">Prioridade sugerida</span>
      <Link href={`/sinais/${signal.id}`} className="mt-2 block text-sm font-semibold leading-snug text-encontro underline-offset-2 group-hover:text-igarape-ink hover:underline">
        {signal.title}
      </Link>
      <p className="mt-1 text-xs text-grafite">{signal.condition}</p>
      {signal.symptoms.length ? <p className="mt-1 line-clamp-2 text-[11px] leading-snug text-ardosia">{signal.symptoms.join(', ')}</p> : null}
      <div className="mt-3 flex items-start gap-1.5 text-[11px] text-ardosia">
        <MapPin className="mt-0.5 size-3 shrink-0" aria-hidden />
        <span>{signal.neighborhood}, {signal.municipality}<br />{formatPeriod(signal.periodStart, signal.periodEnd)}</span>
      </div>
      <div className="mt-3 flex items-center justify-between gap-2 border-t border-agua pt-2">
        <span className="text-xs font-semibold text-grafite">{counts.total} {counts.total === 1 ? 'fonte' : 'fontes'}</span>
        <SourceCounts media={counts.midia} community={counts.comunidade} />
      </div>
      <Link href={`/sinais/${signal.id}#decisao`} className="mt-2 flex min-h-9 items-center justify-between rounded-sm bg-vitoria-soft px-2.5 text-xs font-semibold text-igarape-ink hover:bg-vitoria">
        Revisar na investigação<ArrowRight className="size-3.5" aria-hidden />
      </Link>
    </article>
  )
}

function WorkflowTable({ signals }: { signals: Signal[] }) {
  return (
    <div className="overflow-x-auto rounded-md border border-agua bg-mineral">
      <table className="w-full min-w-[760px] border-collapse text-left text-sm">
        <caption className="sr-only">Lista acessível do fluxo</caption>
        <thead className="bg-nevoa text-xs text-ardosia"><tr><th scope="col" className="px-3 py-2.5 font-medium">Sinal</th><th scope="col" className="px-3 py-2.5 font-medium">Estado</th><th scope="col" className="px-3 py-2.5 font-medium">Prioridade sugerida</th><th scope="col" className="px-3 py-2.5 font-medium">Território e período</th><th scope="col" className="px-3 py-2.5 font-medium">Evidências</th><th scope="col" className="px-3 py-2.5"><span className="sr-only">Ação</span></th></tr></thead>
        <tbody>{signals.length ? signals.map((signal) => { const counts = signal.sourceCounts ?? { midia: 0, comunidade: 0, total: 0 }; return (
          <tr key={signal.id} className="border-t border-agua align-top">
            <td className="px-3 py-3"><span className="block font-mono text-xs text-ardosia">{signal.code}</span><Link href={`/sinais/${signal.id}`} className="mt-0.5 block max-w-72 font-semibold text-encontro hover:underline">{signal.title}</Link><span className="text-xs text-ardosia">{signal.condition}</span></td>
            <td className="px-3 py-3"><span className="inline-flex items-center gap-1.5 whitespace-nowrap"><StateGlyph state={signal.state} />{COLUMN_META[signal.state].title}</span></td>
            <td className="px-3 py-3"><PriorityBadge priority={signal.priority} showSuggested={false} withTooltip={false} /></td>
            <td className="px-3 py-3"><span className="inline-flex items-center gap-1"><MapPin className="size-3" aria-hidden />{signal.neighborhood}</span><span className="block text-xs text-ardosia">{formatPeriod(signal.periodStart, signal.periodEnd)}</span></td>
            <td className="px-3 py-3"><span className="block text-xs">{counts.total} {counts.total === 1 ? 'fonte' : 'fontes'}</span><SourceCounts media={counts.midia} community={counts.comunidade} /></td>
            <td className="px-3 py-3"><Link href={`/sinais/${signal.id}#decisao`} className="inline-flex items-center gap-1 whitespace-nowrap font-medium text-igarape hover:underline"><ShieldCheck className="size-4" aria-hidden />Revisar</Link></td>
          </tr>
        ) }) : <tr><td colSpan={6} className="px-4 py-10 text-center text-sm text-ardosia">Nenhum sinal corresponde aos filtros atuais.</td></tr>}</tbody>
      </table>
    </div>
  )
}

function ViewLink({ href, active, children }: { href: string; active: boolean; children: React.ReactNode }) {
  return <Link href={href} aria-current={active ? 'page' : undefined} className={cn('inline-flex h-8 items-center gap-1.5 rounded-sm px-2.5 text-xs font-medium', active ? 'bg-mineral text-encontro shadow-sm' : 'text-ardosia hover:text-encontro')}>{children}</Link>
}

function groupSignals(signals: Signal[]): Record<WorkflowState, Signal[]> {
  const groups: Record<WorkflowState, Signal[]> = { detectado: [], triagem: [], verificacao: [], avaliacao_risco: [], encerrado: [] }
  for (const signal of signals) groups[signal.state].push(signal)
  return groups
}

function boardViewHref(queryString: string, view: 'board' | 'list'): string {
  const search = new URLSearchParams(queryString)
  search.set('view', view)
  return `/kanban?${search.toString()}`
}
