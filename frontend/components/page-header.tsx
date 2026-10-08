import type { ReactNode } from 'react'

export function PageHeader({
  title,
  description,
  meta,
  actions,
  eyebrow,
}: {
  title: string
  description?: ReactNode
  meta?: ReactNode
  actions?: ReactNode
  eyebrow?: ReactNode
}) {
  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
      <div className="min-w-0">
        {eyebrow}
        <h1 className="text-xl font-semibold tracking-tight text-encontro text-balance md:text-2xl">{title}</h1>
        {description && <p className="mt-1 text-sm leading-relaxed text-ardosia text-pretty">{description}</p>}
        {meta && <div className="mt-1.5 text-xs text-ardosia">{meta}</div>}
      </div>
      {actions && <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div>}
    </div>
  )
}
