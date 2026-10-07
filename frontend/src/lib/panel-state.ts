export type PanelState = 'ready' | 'loading' | 'empty' | 'unavailable'

const panelStates: Record<string, PanelState> = {
  carregando: 'loading',
  vazio: 'empty',
  indisponivel: 'unavailable',
}

/**
 * Estados de interface demonstráveis durante a fundação do painel. Eles não
 * representam estados epidemiológicos nem alteram o fluxo de decisão humana.
 */
export function resolvePanelState(value: string | undefined): PanelState {
  return value ? (panelStates[value] ?? 'ready') : 'ready'
}
