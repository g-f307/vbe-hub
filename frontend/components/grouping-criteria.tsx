import { CircleCheck, CircleDashed } from 'lucide-react'
import type { GroupingCriterion } from '@/lib/types'

export function GroupingCriteria({ criteria }: { criteria: GroupingCriterion[] }) {
  return (
    <section aria-labelledby="criterios-titulo" className="rounded-md border border-agua bg-mineral px-4 py-4 md:px-5">
      <h2 id="criterios-titulo" className="text-base font-semibold text-encontro">
        Por que estes registros foram agrupados?
      </h2>
      <p className="mt-1 text-sm text-ardosia">Critérios usados pelo sistema para sugerir o agrupamento.</p>
      <ul className="mt-3 grid gap-2 sm:grid-cols-2">
        {criteria.map((c) => (
          <li key={c.label} className="flex gap-2.5 rounded-sm border border-agua px-3 py-2.5">
            {c.met ? (
              <CircleCheck className="mt-0.5 size-4 shrink-0 text-igarape" aria-hidden />
            ) : (
              <CircleDashed className="mt-0.5 size-4 shrink-0 text-ardosia" aria-hidden />
            )}
            <div>
              <p className="text-sm font-medium text-grafite">
                {c.label}
                <span className="sr-only">{c.met ? ': atendido' : ': não atendido'}</span>
              </p>
              <p className="text-sm text-pretty text-ardosia">{c.detail}</p>
            </div>
          </li>
        ))}
      </ul>
    </section>
  )
}
