import { proxyComposeInvestigation } from '@/lib/investigation-proxy'

export const dynamic = 'force-dynamic'

export async function POST(request: Request) {
  return proxyComposeInvestigation(request)
}
