'use client'

import { AlertTriangle } from 'lucide-react'

import { Header } from '@/v0/components/header'

export default function ErrorPage({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <div className="min-h-screen bg-background">
      <Header />
      <main id="conteudo-principal" className="mx-auto max-w-2xl px-4 py-16 text-center">
        <AlertTriangle className="mx-auto size-9 text-destructive" aria-hidden />
        <h1 className="mt-4 text-xl font-semibold">Não foi possível carregar os sinais</h1>
        <p className="mt-2 text-sm text-muted-foreground">A API está indisponível ou retornou uma resposta inválida. Nenhum dado de demonstração foi usado como substituto.</p>
        <button type="button" onClick={reset} className="mt-6 min-h-11 rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground">Tentar novamente</button>
      </main>
    </div>
  )
}
