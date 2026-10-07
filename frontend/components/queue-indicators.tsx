import { ArrowDownRight, ArrowRight, ArrowUpRight, GitCompareArrows, Inbox, Scale, SearchCheck } from 'lucide-react'
import type { QueueIndicator } from '@/lib/types'
import { cn } from '@/lib/utils'

const ICONS: Record<QueueIndicator['key'], typeof Inbox> = {
  triagem: Inbox,
  verificacao: SearchCheck,
  avaliacao_risco: Scale,
  conflito: GitCompareArrows,
  detectado: Inbox,
  encerrado: Inbox,
}

const TREND_ICON = { up: ArrowUpRight, down: ArrowDownRight, flat: ArrowRight }

export function QueueIndicators({ indicators }: { indicators: QueueIndicator[] }) {
  return (
    <section aria-label="Resumo da fila no período">
      <ul className="grid grid-cols-2 overflow-hidden rounded-md border border-agua bg-mineral lg:grid-cols-4">
        {indicators.map((item, index) => {
          const Icon = ICONS[item.key]
          const Trend = TREND_ICON[item.trend]
          const isConflict = item.key === 'conflito'
          return (
            <li
              key={item.key}
              className={cn(
                'flex items-center gap-3 px-4 py-3',
                index % 2 === 1 && 'border-l border-agua',
                index >= 2 && 'border-t border-agua lg:border-t-0',
                index === 2 && 'lg:border-l',
              )}
            >
              <span
                className={cn(
                  'flex size-8 shrink-0 items-center justify-center rounded-md',
                  isConflict ? 'bg-urucum-soft text-urucum-ink' : 'bg-vitoria-soft text-igarape-ink',
                )}
                aria-hidden
              >
                <Icon className="size-4" />
              </span>
              <div className="min-w-0">
                <p className="flex items-baseline gap-2">
                  <span className="text-lg font-semibold leading-none text-encontro">{item.value}</span>
                  <span className="truncate text-sm text-grafite">{item.label}</span>
                </p>
                <p className="mt-1 inline-flex items-center gap-1 text-xs text-ardosia">
                  <Trend className="size-3" aria-hidden />
                  {item.trendLabel}
                </p>
              </div>
            </li>
          )
        })}
      </ul>
    </section>
  )
}
