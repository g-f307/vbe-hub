import type { Metadata } from 'next'
import { PanoramaBoard } from '@/components/panorama-board'
import { getGeographicSummary } from '@/lib/panorama-read'

export const metadata: Metadata = { title: 'Panorama' }
export const dynamic = 'force-dynamic'

export default async function PanoramaPage() {
  const summary = await getGeographicSummary()
  return <PanoramaBoard summary={summary} />
}
