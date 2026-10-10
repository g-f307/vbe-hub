import { Skeleton } from '@/components/ui/skeleton'

export default function SignalLoading() {
  return <div className="mx-auto flex w-full max-w-[1440px] flex-col gap-5 px-4 py-5 md:px-6 md:py-6 lg:px-8" aria-label="Carregando investigação do sinal"><Skeleton className="h-28 w-full" /><Skeleton className="h-16 w-full" /><Skeleton className="h-80 w-full" /></div>
}
