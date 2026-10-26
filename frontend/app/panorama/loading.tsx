import { Skeleton } from '@/components/ui/skeleton'

export default function PanoramaLoading() {
  return (
    <div className="mx-auto flex w-full max-w-[1440px] flex-col gap-5 px-4 py-5 md:px-6 md:py-6 lg:px-8" aria-label="Carregando panorama territorial">
      <Skeleton className="h-20 w-full" />
      <Skeleton className="h-24 w-full" />
      <Skeleton className="h-[440px] w-full" />
    </div>
  )
}
