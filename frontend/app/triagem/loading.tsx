import { Skeleton } from '@/components/ui/skeleton'

export default function TriageLoading() {
  return <div className="mx-auto flex w-full max-w-[1440px] flex-col gap-5 px-4 py-5 md:px-6 md:py-6 lg:px-8" aria-label="Carregando fila de sinais"><Skeleton className="h-20 w-full" /><Skeleton className="h-28 w-full" /><Skeleton className="h-96 w-full" /></div>
}
