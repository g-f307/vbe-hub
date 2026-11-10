import type { ReactNode } from 'react'

export function BodySurface({ children }: { children: ReactNode }) {
  return (
    <div className="relative -mt-6 min-h-[calc(100vh-9rem)] rounded-t-3xl bg-background pt-px">
      {children}
    </div>
  )
}
