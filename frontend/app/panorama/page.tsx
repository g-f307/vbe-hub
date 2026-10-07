import type { Metadata } from 'next'
import { PanoramaBoard } from '@/components/panorama-board'

export const metadata: Metadata = { title: 'Panorama' }

export default function PanoramaPage() {
  return <PanoramaBoard />
}
