'use client'

import Link from 'next/link'
import { ArrowRight, Clock3, Link2 } from 'lucide-react'

import { Button } from '@/components/ui/button'

export type EvidenceTimelineItem = {
  addedAt: string
  signal: {
    id: string
    title: string
    body: string
    sourceKind: 'media' | 'community'
    sourceName: string
    publishedAt: string
  }
}

export function EvidenceTimeline({
  items,
  headSignalId,
  compact = false,
  layout = 'timeline',
  onRemove,
}: {
  items: EvidenceTimelineItem[]
  headSignalId: string
  compact?: boolean
  layout?: 'timeline' | 'grid'
  onRemove?: (signalId: string) => void
}) {
  return (
    <div data-evidence-timeline="true" data-evidence-layout={layout} className={layout === 'grid' ? 'grid items-start gap-4 md:grid-cols-2 xl:grid-cols-3' : 'space-y-0'}>
      {items.map((item, index) => (
        <div key={item.signal.id} className={layout === 'timeline' ? 'grid grid-cols-[1.25rem_minmax(0,1fr)] gap-3' : 'min-w-0'}>
          {layout === 'timeline' ? <div className="flex flex-col items-center" aria-hidden>
            <span className="mt-1.5 inline-flex size-5 items-center justify-center rounded-full bg-[#75627F] text-white ring-4 ring-[#F1EDF3]">
              <Link2 className="size-3" />
            </span>
            {index < items.length - 1 ? <span className="min-h-5 w-px flex-1 bg-[#CFC5D4]" /> : null}
          </div> : null}
          <article data-evidence-card="incorporated" className="mb-3 w-full rounded-xl border border-t-4 border-border border-t-[#75627F] bg-background p-3.5 shadow-sm">
            <div className={`flex items-center gap-2 ${layout === 'grid' ? 'justify-between' : 'justify-end'}`}>
              {layout === 'grid' ? <span className="inline-flex size-6 shrink-0 items-center justify-center rounded-full bg-[#75627F] text-white"><Link2 className="size-3.5" aria-hidden /></span> : null}
              <span className="inline-flex items-center gap-1 text-[11px] text-muted-foreground">
                <Clock3 className="size-3" aria-hidden />
                Incorporado em {formatDate(item.addedAt)}
              </span>
            </div>
            <h3 className="mt-2 text-sm font-semibold leading-snug">{item.signal.title}</h3>
            <p className={`${compact ? 'line-clamp-3' : 'line-clamp-4'} mt-1.5 whitespace-pre-wrap text-xs leading-5 text-muted-foreground`}>{item.signal.body}</p>
            <div className={`mt-3 flex flex-wrap items-center gap-2 border-t border-border pt-2.5 ${onRemove ? 'justify-between' : 'justify-end'}`}>
              {onRemove ? <Button type="button" variant="destructive" size="sm" onClick={() => onRemove(item.signal.id)}>Remover evidência</Button> : null}
              <Link
                href={`/sinais/${item.signal.id}?${new URLSearchParams({ returnTo: `/sinais/${headSignalId}?tab=overview` })}`}
                className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline"
              >
                Ver detalhes <ArrowRight className="size-3.5" aria-hidden />
              </Link>
            </div>
          </article>
        </div>
      ))}
    </div>
  )
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat('pt-BR', {
    dateStyle: 'short',
    timeStyle: 'short',
    timeZone: 'America/Manaus',
  }).format(new Date(value))
}
