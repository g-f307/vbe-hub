import type { Metadata, Viewport } from 'next'
import { AppShell } from '@/components/app-shell'
import { Toaster } from '@/components/ui/sonner'
import { TooltipProvider } from '@/components/ui/tooltip'
import './globals.css'

export const metadata: Metadata = {
  title: {
    default: 'VBE Hub — Vigilância Baseada em Eventos',
    template: '%s · VBE Hub',
  },
  description:
    'Ferramenta interna para triagem e revisão humana de sinais de vigilância baseada em eventos a partir de notícias e relatos comunitários sintéticos.',
  generator: 'v0.app',
  robots: { index: false, follow: false },
}

export const viewport: Viewport = {
  colorScheme: 'light',
  themeColor: '#102F3C',
  width: 'device-width',
  initialScale: 1,
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="pt-BR">
      <body className="antialiased">
        <TooltipProvider delay={250}>
          <AppShell>{children}</AppShell>
        </TooltipProvider>
        <Toaster theme="light" position="bottom-right" />
      </body>
    </html>
  )
}
