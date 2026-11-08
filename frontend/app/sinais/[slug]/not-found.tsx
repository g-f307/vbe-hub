import Link from 'next/link'
import { SearchX } from 'lucide-react'

import { Header } from '@/v0/components/header'

export default function SignalNotFound() {
  return (
    <div className="min-h-screen bg-background">
      <Header />
      <main id="conteudo-principal" className="mx-auto max-w-2xl px-4 py-16 text-center">
        <SearchX className="mx-auto size-9 text-muted-foreground" aria-hidden />
        <h1 className="mt-4 text-xl font-semibold">Sinal não encontrado</h1>
        <p className="mt-2 text-sm text-muted-foreground">O identificador não existe ou o sinal não está acessível. Nenhum conteúdo foi inventado para esta página.</p>
        <Link href="/" className="mt-6 inline-flex min-h-11 items-center rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground">Voltar para detectados</Link>
      </main>
    </div>
  )
}
