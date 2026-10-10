import { Bot, UserRound } from 'lucide-react'
import { formatDateTime } from '@/lib/format'
import type { AuditEvent } from '@/lib/types'
import { cn } from '@/lib/utils'

export function AuditTimeline({ events }: { events: AuditEvent[] }) {
  const hasHumanDecision = events.some((e) => e.actor === 'analista')
  return (
    <section aria-labelledby="historico-titulo" className="rounded-md border border-agua bg-mineral px-4 py-4 md:px-5">
      <h2 id="historico-titulo" className="text-base font-semibold text-encontro">
        Histórico de auditoria
      </h2>
      <p className="mt-1 text-sm text-ardosia">Registro imutável das ações do sistema e da vigilância.</p>

      <ol className="mt-4 flex flex-col">
        {events.map((event, index) => {
          const Icon = event.actor === 'sistema' ? Bot : UserRound
          return (
            <li key={event.id} className="flex gap-3">
              <div className="flex w-7 shrink-0 flex-col items-center" aria-hidden>
                <span
                  className={cn(
                    'flex size-7 items-center justify-center rounded-full',
                    event.actor === 'sistema' ? 'bg-muted text-ardosia' : 'bg-igarape text-mineral',
                  )}
                >
                  <Icon className="size-3.5" />
                </span>
                {(index < events.length - 1 || !hasHumanDecision) && <span className="w-px flex-1 bg-agua-strong" />}
              </div>
              <div className="min-w-0 flex-1 pb-4">
                <p className="text-sm font-medium text-grafite">
                  {event.title}
                  <span className="ml-2 text-xs font-normal text-ardosia">
                    {event.actor === 'sistema' ? 'Sistema' : event.actorLabel ?? 'Analista'}
                  </span>
                </p>
                <p className="text-sm text-pretty text-ardosia">{event.description}</p>
                <time dateTime={event.at} className="mt-0.5 block font-mono text-xs text-ardosia">
                  {formatDateTime(event.at)}
                </time>
              </div>
            </li>
          )
        })}
        {!hasHumanDecision && (
          <li className="flex gap-3">
            <div className="flex w-7 shrink-0 justify-center" aria-hidden>
              <span className="size-7 rounded-full border-2 border-dashed border-agua-strong" />
            </div>
            <p className="flex-1 rounded-sm border border-dashed border-agua-strong px-3 py-2 text-sm text-ardosia">
              Próximas decisões humanas aparecerão aqui.
            </p>
          </li>
        )}
      </ol>
    </section>
  )
}
