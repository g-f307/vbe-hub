'use client'

import Link from 'next/link'
import { Clock3, Link2 } from 'lucide-react'

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
  onRemove,
}: {
  items: EvidenceTimelineItem[]
  headSignalId: string
  compact?: boolean
  onRemove?: (signalId: string) => void
}) {
  return (
    <div data-evidence-timeline="true" className="space-y-0">
      {items.map((item, index) => (
        <div key={item.signal.id} className="grid grid-cols-[1.25rem_minmax(0,1fr)] gap-3">
          <div className="flex flex-col items-center" aria-hidden>
            <span className="mt-1.5 inline-flex size-5 items-center justify-center rounded-full bg-[#75627F] text-white ring-4 ring-[#F1EDF3]">
              <Link2 className="size-3" />
            </span>
            {index < items.length - 1 ? <span className="min-h-5 w-px flex-1 bg-[#CFC5D4]" /> : null}
          </div>
          <article data-evidence-card="incorporated" className="mb-3 rounded-xl border border-t-4 border-border border-t-[#75627F] bg-background p-3.5 shadow-sm">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="text-xs font-medium text-[#67536F]">Evidência incorporada</span>
              <span className="inline-flex items-center gap-1 text-[11px] text-muted-foreground">
                <Clock3 className="size-3" aria-hidden />
                Incorporado em {formatDate(item.addedAt)}
              </span>
            </div>
            <p className="mt-2 text-[11px] text-muted-foreground">
              {sourceLabel(item.signal.sourceKind, item.signal.sourceName)} · publicado em {formatDate(item.signal.publishedAt)}
            </p>
            <h3 className="mt-1 text-sm font-semibold leading-snug">{item.signal.title}</h3>
            <p className={`${compact ? 'line-clamp-3' : 'line-clamp-4'} mt-1.5 whitespace-pre-wrap text-xs leading-5 text-muted-foreground`}>{item.signal.body}</p>
            <div className="mt-3 flex flex-wrap items-center justify-between gap-2 border-t border-border pt-2.5">
              <Link
                href={`/sinais/${item.signal.id}?${new URLSearchParams({ returnTo: `/sinais/${headSignalId}?tab=overview` })}`}
                className="text-xs font-medium text-primary hover:underline"
              >
                Abrir ficha para consulta
              </Link>
              {onRemove ? <Button type="button" variant="destructive" size="sm" onClick={() => onRemove(item.signal.id)}>Remover evidência</Button> : null}
            </div>
          </article>
        </div>
      ))}
    </div>
  )
}

function sourceLabel(kind: 'media' | 'community', name: string): string {
  if (name.startsWith('demo-')) return kind === 'media' ? 'Mídia' : 'Relato comunitário'
  return name
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat('pt-BR', {
    dateStyle: 'short',
    timeStyle: 'short',
    timeZone: 'America/Manaus',
  }).format(new Date(value))
}
