'use client'

import { useEffect, useRef } from 'react'
import Link from 'next/link'
import { ChevronDown, Columns3, LayoutGrid, List } from 'lucide-react'

export type DetectedView = 'cards' | 'list' | 'kanban'

export function ViewSelector({ view, hrefs }: { view: DetectedView; hrefs: Record<DetectedView, string> }) {
  const detailsRef = useRef<HTMLDetailsElement>(null)
  const active = VIEW_META[view]
  const ActiveIcon = active.icon

  useEffect(() => {
    const close = () => {
      if (detailsRef.current) detailsRef.current.open = false
    }
    const handlePointerDown = (event: PointerEvent) => {
      if (detailsRef.current?.open && !detailsRef.current.contains(event.target as Node)) close()
    }
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') close()
    }
    document.addEventListener('pointerdown', handlePointerDown)
    document.addEventListener('keydown', handleKeyDown)
    return () => {
      document.removeEventListener('pointerdown', handlePointerDown)
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [])

  return (
    <div className="rounded-xl border border-border bg-card p-3 shadow-sm lg:w-52">
      <details ref={detailsRef} className="group relative" data-view={view} data-close-on-outside="true">
        <summary aria-label="Selecionar visualização" className="flex min-h-11 cursor-pointer list-none items-center justify-between gap-3 rounded-md border border-input bg-background px-3 text-[13px] font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring [&::-webkit-details-marker]:hidden">
          <span className="flex items-center gap-2">
            <span className="inline-flex size-7 items-center justify-center rounded-md bg-primary/10 text-primary"><ActiveIcon className="size-4" aria-hidden /></span>
            {active.label}
          </span>
          <ChevronDown className="size-4 text-muted-foreground transition-transform group-open:rotate-180" aria-hidden />
        </summary>
        <div className="absolute right-0 z-20 mt-1 grid w-full min-w-48 gap-1 rounded-lg border border-border bg-card p-1.5 shadow-lg">
          {(Object.entries(VIEW_META) as Array<[DetectedView, (typeof VIEW_META)[DetectedView]]>).map(([value, meta]) => {
            const Icon = meta.icon
            return (
              <Link key={value} href={hrefs[value]} onClick={() => { if (detailsRef.current) detailsRef.current.open = false }} aria-current={view === value ? 'true' : undefined} className={`flex min-h-10 items-center gap-2 rounded-md px-2.5 text-[13px] font-medium ${view === value ? 'bg-primary text-primary-foreground' : 'text-foreground hover:bg-muted'}`}>
                <span className={`inline-flex size-7 items-center justify-center rounded-md ${view === value ? 'bg-white/15 text-white' : 'bg-primary/10 text-primary'}`}><Icon className="size-4" aria-hidden /></span>
                {meta.label}
              </Link>
            )
          })}
        </div>
      </details>
    </div>
  )
}

const VIEW_META = {
  cards: { label: 'Cards', icon: LayoutGrid },
  list: { label: 'Lista', icon: List },
  kanban: { label: 'Kanban', icon: Columns3 },
} satisfies Record<DetectedView, { label: string; icon: typeof LayoutGrid }>
