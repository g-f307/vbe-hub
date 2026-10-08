import Link from 'next/link'
import { ChevronLeft } from 'lucide-react'
import { PriorityBadge, StateLabel } from '@/components/status-badges'
import { formatRelative } from '@/lib/format'
import type { Signal, WorkflowState } from '@/lib/types'

export function SignalHeader({
  signal,
  state,
  updatedAt,
}: {
  signal: Signal
  state: WorkflowState
  updatedAt: string
}) {
  return (
    <header className="flex flex-col gap-3">
      <nav aria-label="Trilha de navegação" className="flex items-center gap-1 text-sm text-ardosia">
        <Link
          href="/triagem"
          className="-ml-1 inline-flex min-h-11 items-center gap-1 rounded-sm px-1 hover:text-encontro md:min-h-0"
        >
          <ChevronLeft className="size-4" aria-hidden />
          Triagem
        </Link>
        <span aria-hidden>/</span>
        <span className="font-mono text-xs text-grafite" aria-current="page">
          {signal.code}
        </span>
      </nav>

      <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <div className="min-w-0">
          <p className="font-mono text-xs tracking-wide text-ardosia">{signal.code}</p>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight text-balance text-encontro md:text-[28px]">
            {signal.title}
          </h1>
          <p className="mt-1 text-sm text-pretty text-ardosia">{signal.subtitle}</p>
        </div>
        <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
          <PriorityBadge priority={signal.priority} />
          <StateLabel state={state} />
          <span className="text-sm text-ardosia">
            Atualizado <time dateTime={updatedAt}>{formatRelative(updatedAt)}</time>
          </span>
        </div>
      </div>
    </header>
  )
}
