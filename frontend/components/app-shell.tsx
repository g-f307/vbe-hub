'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useState, type ReactNode } from 'react'
import { BookOpenText, CircleHelp, Database, ListChecks, Map, PanelLeftClose, PanelLeftOpen } from 'lucide-react'
import { HelpDialog, MethodSheet } from '@/components/info-panels'
import { VbeMark } from '@/components/vbe-logo'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { formatDateTime } from '@/lib/format'
import { LAST_UPDATED_ISO } from '@/lib/mock-data'
import { cn } from '@/lib/utils'

const NAV_ITEMS = [
  { href: '/triagem', label: 'Triagem', icon: ListChecks, match: ['/triagem', '/sinais'] },
  { href: '/panorama', label: 'Panorama', icon: Map, match: ['/panorama'] },
]

function contextTitle(pathname: string) {
  if (pathname.startsWith('/sinais')) return 'Investigação de sinal'
  if (pathname.startsWith('/panorama')) return 'Panorama'
  return 'Triagem'
}

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname()
  const [expanded, setExpanded] = useState(true)
  const [methodOpen, setMethodOpen] = useState(false)
  const [helpOpen, setHelpOpen] = useState(false)
  const showLabels = expanded

  return (
    <div className="flex min-h-dvh bg-nevoa">
      <a
        href="#conteudo"
        className="sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-50 focus:rounded-md focus:bg-mineral focus:px-3 focus:py-2 focus:text-sm"
      >
        Pular para o conteúdo
      </a>

      <aside
        aria-label="Navegação principal"
        className={cn(
          'sticky top-0 hidden h-dvh shrink-0 flex-col bg-encontro text-agua transition-[width] duration-200 md:flex md:w-[76px]',
          expanded && 'xl:w-56',
        )}
      >
        <div className="flex h-14 items-center gap-2.5 px-[22px]">
          <VbeMark className="size-8 shrink-0 text-vitoria" />
          <span className={cn('hidden text-[15px] font-semibold tracking-tight text-mineral', showLabels && 'xl:inline')}>
            VBE Hub
          </span>
        </div>

        <nav className="mt-3 flex flex-1 flex-col gap-1 px-3">
          {NAV_ITEMS.map((item) => {
            const active = item.match.some((m) => pathname.startsWith(m))
            return (
              <SidebarLink key={item.href} label={item.label} showLabel={showLabels}>
                <Link
                  href={item.href}
                  aria-current={active ? 'page' : undefined}
                  className={cn(
                    'relative flex h-11 items-center gap-3 rounded-md px-[14px] text-sm font-medium transition-colors',
                    active ? 'bg-encontro-soft text-mineral' : 'text-agua hover:bg-encontro-soft/60 hover:text-mineral',
                  )}
                >
                  {active && <span className="absolute top-2 bottom-2 left-0 w-0.5 rounded-full bg-vitoria" aria-hidden />}
                  <item.icon className="size-5 shrink-0" aria-hidden />
                  <span className={cn('sr-only', showLabels && 'xl:not-sr-only')}>{item.label}</span>
                </Link>
              </SidebarLink>
            )
          })}

          <div className="my-3 h-px bg-sidebar-border" role="separator" />

          <SidebarLink label="Método e limites" showLabel={showLabels}>
            <button
              type="button"
              onClick={() => setMethodOpen(true)}
              className="flex h-11 w-full items-center gap-3 rounded-md px-[14px] text-left text-sm font-medium text-agua transition-colors hover:bg-encontro-soft/60 hover:text-mineral"
            >
              <BookOpenText className="size-5 shrink-0" aria-hidden />
              <span className={cn('sr-only', showLabels && 'xl:not-sr-only')}>Método e limites</span>
            </button>
          </SidebarLink>
        </nav>

        <div className="flex flex-col gap-3 px-3 pb-4">
          <div
            className={cn('flex items-center gap-2 rounded-md border border-sidebar-border px-[14px] py-2 text-xs text-vitoria')}
            title="Todos os dados são sintéticos"
          >
            <Database className="size-4 shrink-0" aria-hidden />
            <span className={cn('sr-only', showLabels && 'xl:not-sr-only')}>Dados sintéticos</span>
          </div>
          <div className="flex items-center gap-2.5 px-[10px]">
            <span
              className="flex size-8 shrink-0 items-center justify-center rounded-full bg-vitoria text-xs font-semibold text-encontro"
              aria-hidden
            >
              AV
            </span>
            <span className={cn('sr-only text-xs leading-tight text-agua', showLabels && 'xl:not-sr-only')}>
              Analista de vigilância
            </span>
          </div>
          <button
            type="button"
            onClick={() => setExpanded((v) => !v)}
            aria-label={expanded ? 'Recolher menu lateral' : 'Expandir menu lateral'}
            aria-expanded={expanded}
            className="hidden h-9 items-center justify-center rounded-md text-agua hover:bg-encontro-soft hover:text-mineral xl:flex"
          >
            {expanded ? <PanelLeftClose className="size-4" aria-hidden /> : <PanelLeftOpen className="size-4" aria-hidden />}
          </button>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-30 flex h-14 items-center gap-3 border-b border-agua bg-mineral/95 px-4 md:px-6">
          <VbeMark className="size-7 shrink-0 text-encontro md:hidden" title="VBE Hub" />
          <p className="truncate text-sm font-semibold text-encontro">{contextTitle(pathname)}</p>
          <span className="hidden text-sm text-ardosia lg:inline">
            · Atualizado em {formatDateTime(LAST_UPDATED_ISO)}
          </span>
          <div className="ml-auto flex items-center gap-2">
            <span className="inline-flex items-center gap-1.5 rounded-sm border border-dashed border-agua-strong px-2 py-1 text-xs text-ardosia">
              <span className="size-1.5 rounded-full bg-andiroba" aria-hidden />
              <span className="hidden sm:inline">Ambiente de demonstração</span>
              <span className="sm:hidden">Demonstração</span>
            </span>
            <button
              type="button"
              onClick={() => setHelpOpen(true)}
              aria-label="Abrir ajuda"
              className="flex size-11 items-center justify-center rounded-md text-ardosia hover:bg-muted hover:text-encontro md:size-9"
            >
              <CircleHelp className="size-5" aria-hidden />
            </button>
          </div>
        </header>

        <main id="conteudo" className="flex-1 pb-24 md:pb-0">
          {children}
        </main>
      </div>

      <nav
        aria-label="Navegação principal"
        className="fixed inset-x-0 bottom-0 z-40 grid grid-cols-3 border-t border-sidebar-border bg-encontro pb-[env(safe-area-inset-bottom)] md:hidden"
      >
        {NAV_ITEMS.map((item) => {
          const active = item.match.some((m) => pathname.startsWith(m))
          return (
            <Link
              key={item.href}
              href={item.href}
              aria-current={active ? 'page' : undefined}
              className={cn(
                'flex min-h-14 flex-col items-center justify-center gap-0.5 text-xs font-medium',
                active ? 'text-vitoria' : 'text-agua',
              )}
            >
              <item.icon className="size-5" aria-hidden />
              {item.label}
            </Link>
          )
        })}
        <button
          type="button"
          onClick={() => setMethodOpen(true)}
          className="flex min-h-14 flex-col items-center justify-center gap-0.5 text-xs font-medium text-agua"
        >
          <BookOpenText className="size-5" aria-hidden />
          Método
        </button>
      </nav>

      <MethodSheet open={methodOpen} onOpenChange={setMethodOpen} />
      <HelpDialog open={helpOpen} onOpenChange={setHelpOpen} />
    </div>
  )
}

function SidebarLink({ label, showLabel, children }: { label: string; showLabel: boolean; children: ReactNode }) {
  return (
    <Tooltip>
      <TooltipTrigger render={<div className={cn(showLabel && 'xl:contents')} />}>{children}</TooltipTrigger>
      <TooltipContent side="right" className={cn(showLabel && 'xl:hidden')}>
        {label}
      </TooltipContent>
    </Tooltip>
  )
}
