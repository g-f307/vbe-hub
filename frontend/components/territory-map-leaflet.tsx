'use client'

import type { PathOptions } from 'leaflet'
import { MapContainer, Polygon, Tooltip } from 'react-leaflet'
import type { GeographicArea } from '@/lib/panorama-read'
import { geometryForArea } from '@/lib/territory-geometry'

const DEFAULT_CENTER: [number, number] = [-3.08, -60.015]
const ACTIVE_STYLE: PathOptions = { color: '#9c3f2a', fillColor: '#c85c43', fillOpacity: 0.72, weight: 3 }
const INACTIVE_STYLE: PathOptions = { color: '#0f5b58', fillColor: '#14736f', fillOpacity: 0.48, weight: 2 }

export function TerritoryMapLeaflet({
  areas,
  selectedKey,
  onSelect,
}: {
  areas: GeographicArea[]
  selectedKey: string | null
  onSelect: (key: string) => void
}) {
  return (
    <div className="relative min-h-[360px] size-full">
      <MapContainer
        center={DEFAULT_CENTER}
        zoom={11}
        minZoom={10}
        maxZoom={14}
        scrollWheelZoom={false}
        attributionControl={false}
        className="min-h-[440px] size-full bg-nevoa"
      >
        {areas.map((area) => {
          const geometry = geometryForArea(area.municipality, area.district)
          if (!geometry) return null
          const positions = geometry.polygon.map(([longitude, latitude]) => [latitude, longitude] as [number, number])
          return (
            <Polygon
              key={`${area.key}-${selectedKey === area.key ? 'active' : 'idle'}`}
              positions={positions}
              pathOptions={selectedKey === area.key ? ACTIVE_STYLE : INACTIVE_STYLE}
              eventHandlers={{ click: () => onSelect(area.key) }}
            >
              <Tooltip direction="top" opacity={1} sticky>
                <span className="font-semibold">{area.district}</span><br />
                {area.signals} sinal{area.signals === 1 ? '' : 'is'}
              </Tooltip>
            </Polygon>
          )
        })}
      </MapContainer>
      <div className="pointer-events-none absolute right-3 bottom-3 z-[500] max-w-64 rounded-sm border border-agua bg-mineral/95 px-2.5 py-2 text-xs leading-relaxed text-ardosia shadow-sm">
        Contornos esquemáticos para demonstração, sem localização individual.
      </div>
    </div>
  )
}
