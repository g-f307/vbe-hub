import type { Metadata } from 'next'
import { PanoramaBoard } from '@/components/panorama-board'
import { getGeographicSummary } from '@/lib/panorama-read'
import { Header } from '@/v0/components/header'

export const metadata: Metadata = { title: 'Panorama' }
export const dynamic = 'force-dynamic'

export default async function PanoramaPage() {
  const summary = await getGeographicSummary()
  return (
    <div className="min-h-screen bg-background">
      <Header />
      <PanoramaBoard summary={summary} />
    </div>
  )
}
