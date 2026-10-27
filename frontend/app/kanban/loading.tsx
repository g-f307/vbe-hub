import { Skeleton } from '@/components/ui/skeleton'

export default function WorkflowLoading() {
  return (
    <div className="mx-auto flex w-full max-w-[1680px] flex-col gap-5 px-4 py-5 md:px-6 md:py-6 lg:px-8" aria-label="Carregando fluxo dos sinais">
      <Skeleton className="h-20 w-full" />
      <Skeleton className="h-24 w-full" />
      <div className="grid gap-3 lg:grid-cols-5">{Array.from({ length: 5 }, (_, index) => <Skeleton key={index} className="h-80 w-full" />)}</div>
    </div>
  )
}
