import { notFound } from 'next/navigation'
import { SignalInvestigation } from '@/components/signal-investigation'
import { SignalReadError, getSignalDetail } from '@/lib/signal-read'

export default async function SignalPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params
  let detail
  try {
    detail = await getSignalDetail(slug)
  } catch (error) {
    if (error instanceof SignalReadError && error.kind === 'not-found') notFound()
    throw error
  }
  return <SignalInvestigation signal={detail.signal} sources={detail.sources} criteria={detail.criteria} audit={detail.audit} workflow={detail.workflow} reviewTargets={detail.reviewTargets} />
}
