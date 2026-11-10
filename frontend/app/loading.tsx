import { Header } from '@/v0/components/header'
import { BodySurface } from '@/v0/components/body-surface'

export default function Loading() {
  return (
    <div className="min-h-screen bg-primary">
      <Header />
      <BodySurface><main id="conteudo-principal" aria-label="Carregando sinais detectados" className="mx-auto max-w-screen-2xl animate-pulse px-4 py-6 sm:px-6 lg:px-8">
        <div className="h-8 w-64 rounded bg-muted" />
        <div className="mt-3 h-4 w-full max-w-2xl rounded bg-muted" />
        <div className="mt-6 h-20 rounded-xl bg-muted" />
        <div className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {Array.from({ length: 6 }, (_, index) => <div key={index} className="h-64 rounded-xl bg-muted" />)}
        </div>
      </main></BodySurface>
    </div>
  )
}
