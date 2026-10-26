'use client'

import dynamic from 'next/dynamic'
import type { GeographicArea } from '@/lib/panorama-read'

const LeafletTerritoryMap = dynamic(
  () => import('@/components/territory-map-leaflet').then((module) => module.TerritoryMapLeaflet),
  {
    ssr: false,
    loading: () => <div className="flex min-h-[360px] items-center justify-center p-6 text-sm text-ardosia">Preparando geometria local…</div>,
  },
)

export function TerritoryMap({
  areas,
  selectedKey,
  onSelect,
}: {
  areas: GeographicArea[]
  selectedKey: string | null
  onSelect: (key: string) => void
}) {
  if (areas.length === 0) {
    return (
      <div className="flex min-h-[360px] items-center justify-center p-6 text-center">
        <div className="max-w-sm">
          <p className="text-sm font-semibold text-encontro">Geometria indisponível para as áreas atuais</p>
          <p className="mt-1 text-xs leading-relaxed text-ardosia">Use a lista textual para selecionar a área e abrir a fila filtrada.</p>
        </div>
      </div>
    )
  }
  return <LeafletTerritoryMap areas={areas} selectedKey={selectedKey} onSelect={onSelect} />
}
