import { proxyRemoveInvestigationMember } from '@/lib/investigation-proxy'

export const dynamic = 'force-dynamic'

export async function POST(
  request: Request,
  context: { params: Promise<{ fileId: string; signalId: string }> },
) {
  const { fileId, signalId } = await context.params
  return proxyRemoveInvestigationMember(request, fileId, signalId)
}
