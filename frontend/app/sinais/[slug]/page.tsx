import { notFound } from 'next/navigation'
import { SignalInvestigation } from '@/components/signal-investigation'
import { getSignalBySlug } from '@/lib/mock-data'

export default async function SignalPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params
  const signal = getSignalBySlug(slug)

  if (!signal) notFound()

  return <SignalInvestigation signal={signal} />
}
