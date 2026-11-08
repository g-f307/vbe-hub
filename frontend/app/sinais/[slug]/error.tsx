'use client'

import Link from 'next/link'
import { AlertTriangle } from 'lucide-react'

import { Header } from '@/v0/components/header'

export default function SignalError({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <div className="min-h-screen bg-background">
      <Header />
      <main id="conteudo-principal" className="mx-auto max-w-2xl px-4 py-16 text-center">
        <AlertTriangle className="mx-auto size-9 text-destructive" aria-hidden />
        <h1 className="mt-4 text-xl font-semibold">Não foi possível carregar este sinal</h1>
        <p className="mt-2 text-sm text-muted-foreground">O detalhe ou as sugestões relacionadas estão temporariamente indisponíveis. Nenhum conteúdo foi fabricado como substituto.</p>
        <div className="mt-6 flex flex-wrap justify-center gap-3">
          <button type="button" onClick={reset} className="min-h-11 rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground">Tentar novamente</button>
          <Link href="/" className="inline-flex min-h-11 items-center rounded-md border border-border px-4 text-sm font-medium">Voltar para detectados</Link>
        </div>
      </main>
    </div>
  )
}
