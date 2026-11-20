import { safeInternalReturnTo } from './safe-navigation'

export type SignalTab = 'overview' | 'evidence'

export function signalHref(
  id: string,
  tab: SignalTab,
  returnTo: string,
): string {
  return `/sinais/${encodeURIComponent(id)}?${new URLSearchParams({ tab, returnTo: safeInternalReturnTo(returnTo) })}`
}

export function evidenceHref(
  id: string,
  headId: string,
  tab: SignalTab,
  queueHref: string,
): string {
  return `/sinais/${encodeURIComponent(id)}?${new URLSearchParams({ returnTo: signalHref(headId, tab, queueHref) })}`
}

export function resolveSignalTab(tab: string | undefined): {
  tab: SignalTab
  openCandidates: boolean
} {
  return {
    tab: tab === 'evidence' || tab === 'related' ? 'evidence' : 'overview',
    openCandidates: tab === 'related',
  }
}

export function resolveSignalNavigation(
  returnTo: string,
  headId: string | null,
) {
  const safe = safeInternalReturnTo(returnTo)
  if (!headId) return { queueHref: safe, headHref: null }
  const url = new URL(safe, 'http://internal')
  if (url.pathname === `/sinais/${encodeURIComponent(headId)}`) {
    return {
      queueHref: safeInternalReturnTo(
        url.searchParams.get('returnTo') ?? undefined,
      ),
      headHref: safe,
    }
  }
  return {
    queueHref: safe.startsWith('/sinais/') ? '/' : safe,
    headHref: signalHref(
      headId,
      'overview',
      safe.startsWith('/sinais/') ? '/' : safe,
    ),
  }
}
