import { Header } from '@/v0/components/header'

export default function Loading() {
  return (
    <div className="min-h-screen bg-background">
      <Header />
      <main id="conteudo-principal" aria-label="Carregando página do sinal" className="mx-auto max-w-screen-xl animate-pulse px-4 py-6 sm:px-6 lg:px-8">
        <div className="h-11 w-52 rounded bg-muted" />
        <div className="mt-4 h-48 rounded-xl bg-muted" />
        <div className="mt-4 h-12 rounded bg-muted" />
        <div className="mt-6 h-80 rounded-xl bg-muted" />
      </main>
    </div>
  )
}
