import { Header } from '@/v0/components/header'
import { BodySurface } from '@/v0/components/body-surface'

export default function Loading() {
  return (
    <div className="min-h-screen bg-primary">
      <Header />
      <BodySurface><main id="conteudo-principal" aria-label="Carregando página do sinal" className="mx-auto max-w-screen-2xl animate-pulse px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
        <div className="h-11 w-48 rounded bg-muted" />
        <div className="mt-4 h-36 border-l-4 border-muted pl-6"><div className="h-4 w-40 rounded bg-muted" /><div className="mt-5 h-9 max-w-3xl rounded bg-muted" /><div className="mt-3 h-5 max-w-2xl rounded bg-muted" /></div>
        <div className="mt-6 grid gap-px border-y border-border bg-border sm:grid-cols-3">{Array.from({ length: 3 }).map((_, index) => <div key={index} className="h-20 bg-background p-4"><div className="h-3 w-20 rounded bg-muted" /><div className="mt-2 h-4 w-32 rounded bg-muted" /></div>)}</div>
        <div className="mt-5 h-12 border-b border-border bg-muted/50" />
        <div className="mt-8 grid gap-10 xl:grid-cols-[minmax(0,1fr)_320px]"><div className="h-80 rounded-r-xl bg-muted" /><div className="h-56 border-l-2 border-muted pl-5"><div className="h-4 w-36 rounded bg-muted" /></div></div>
      </main></BodySurface>
    </div>
  )
}
