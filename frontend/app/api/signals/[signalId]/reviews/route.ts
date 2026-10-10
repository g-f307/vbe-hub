import { proxyWorkflowPost } from '@/lib/workflow-proxy'

export const dynamic = 'force-dynamic'

export async function POST(request: Request, context: { params: Promise<{ signalId: string }> }) {
  const { signalId } = await context.params
  return proxyWorkflowPost(request, signalId, 'review')
}
