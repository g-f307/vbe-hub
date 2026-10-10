import { TriangleAlert } from 'lucide-react'
import { PriorityBadge, SourceCounts } from '@/components/status-badges'
import { formatPeriod } from '@/lib/format'
import type { Signal } from '@/lib/types'

export function SignalSummary({
  signal,
  sourceCounts,
}: {
  signal: Signal
  sourceCounts: { midia: number; comunidade: number }
}) {
  const total = sourceCounts.midia + sourceCounts.comunidade
  return (
    <section aria-labelledby="resumo-titulo" className="rounded-md border border-agua bg-mineral">
      <div className="border-b border-agua px-4 py-3 md:px-5">
        <h2 id="resumo-titulo" className="text-base font-semibold text-encontro">
          Resumo do sinal
        </h2>
      </div>

      <dl className="grid grid-cols-1 gap-x-6 gap-y-4 px-4 py-4 sm:grid-cols-2 md:px-5 lg:grid-cols-3">
        <SummaryItem term="Condição mencionada">{signal.condition}</SummaryItem>
        <SummaryItem term="Sintomas">
          {signal.symptoms.length > 0 ? (
            <ul className="mt-0.5 flex flex-wrap gap-1.5">
              {signal.symptoms.map((symptom) => (
                <li key={symptom} className="rounded-sm bg-vitoria-soft px-1.5 py-0.5 text-xs font-medium text-igarape-ink">
                  {symptom}
                </li>
              ))}
            </ul>
          ) : 'Não informados'}
        </SummaryItem>
        <SummaryItem term="Localização">
          {signal.municipality}, {signal.neighborhood}
        </SummaryItem>
        <SummaryItem term="Período">{formatPeriod(signal.periodStart, signal.periodEnd)}</SummaryItem>
        <SummaryItem term="Magnitude mencionada">{signal.magnitude ?? 'Não informada'}</SummaryItem>
        <SummaryItem term="Evidências">
          <span className="flex flex-wrap items-center gap-x-3 gap-y-1">
            <span>
              {total} {total === 1 ? 'fonte' : 'fontes'}
            </span>
            <SourceCounts media={sourceCounts.midia} community={sourceCounts.comunidade} />
          </span>
        </SummaryItem>
      </dl>

      <div className="flex flex-col gap-2 border-t border-agua px-4 py-3 md:flex-row md:items-start md:gap-4 md:px-5">
        <div className="shrink-0">
          <PriorityBadge priority={signal.priority} />
        </div>
        <p className="text-sm text-pretty text-grafite">
          <span className="sr-only">Justificativa da prioridade sugerida: </span>
          {signal.priorityRationale}
        </p>
      </div>

      {signal.divergences.length > 0 && (
        <div className="mx-4 mb-4 flex gap-2.5 rounded-sm border border-andiroba/50 bg-andiroba-soft px-3 py-2.5 md:mx-5">
          <TriangleAlert className="mt-0.5 size-4 shrink-0 text-andiroba-ink" aria-hidden />
          <div>
            <p className="text-sm font-semibold text-andiroba-ink">Divergência entre fontes</p>
            <ul className="mt-0.5 text-sm text-pretty text-grafite">
              {signal.divergences.map((d) => (
                <li key={d}>{d}</li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </section>
  )
}

function SummaryItem({ term, children }: { term: string; children: React.ReactNode }) {
  return (
    <div className="min-w-0">
      <dt className="text-xs font-medium tracking-wide text-ardosia uppercase">{term}</dt>
      <dd className="mt-1 text-sm text-grafite">{children}</dd>
    </div>
  )
}
