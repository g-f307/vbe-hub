import type { Metadata, Viewport } from 'next'
import 'leaflet/dist/leaflet.css'
import './globals.css'

export const metadata: Metadata = {
  title: 'VBEHub | Hub de Vigilância Epidemiológica',
  description: 'Sistema integrado para captação e gerenciamento de sinais de saúde pública',
  generator: 'v0.app',
  robots: { index: false, follow: false },
  icons: {
    icon: '/brand/favicon.svg',
    shortcut: '/brand/favicon.svg',
  },
}

export const viewport: Viewport = {
  themeColor: '#155e75',
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
      <body className="font-sans antialiased">
        <a
          href="#conteudo-principal"
          className="sr-only focus:not-sr-only focus:fixed focus:left-3 focus:top-3 focus:z-[1000] focus:rounded-md focus:bg-background focus:px-3 focus:py-2 focus:text-foreground focus:shadow-lg"
        >
          Pular para o conteúdo
        </a>
        {children}
      </body>
    </html>
  )
}
