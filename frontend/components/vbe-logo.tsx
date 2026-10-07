import { cn } from '@/lib/utils'

export function VbeMark({ className, title }: { className?: string; title?: string }) {
  return (
    <svg
      viewBox="0 0 32 32"
      fill="none"
      className={cn('size-8', className)}
      role={title ? 'img' : undefined}
      aria-hidden={title ? undefined : true}
      aria-label={title}
    >
      <path d="M6 7.5 15 15.2M27 10.5 17.2 15.4M10.5 27 15.2 17.4" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" opacity="0.75" />
      <rect x="3.6" y="5.1" width="4.8" height="4.8" rx="0.8" fill="currentColor" />
      <circle cx="27" cy="10.5" r="2.4" stroke="currentColor" strokeWidth="1.4" />
      <path d="m10.5 24.2 2.6 2.8-2.6 2.8-2.6-2.8z" fill="currentColor" />
      <circle cx="16" cy="16" r="4.1" fill="#9FD3C2" />
      <circle cx="16" cy="16" r="1.6" fill="#102F3C" />
    </svg>
  )
}
