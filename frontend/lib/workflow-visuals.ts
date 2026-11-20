import type { IndividualSignalState } from './individual-signal-read'

type VisualStyle = {
  banner: string
  folder: string
  outline: string
  line: string
  surface: string
  rowMarker: string
}
const states: IndividualSignalState[] = [
  'detected',
  'triage',
  'verification',
  'risk_assessment',
  'closed',
]

export const STATE_VISUAL_STYLE = Object.fromEntries(
  states.map((state) => {
    const scope = `workflow-${state}`
    return [
      state,
      {
        banner: `${scope} bg-[var(--workflow-tone)] text-[var(--workflow-ink)]`,
        folder: `${scope} bg-[var(--workflow-soft)]`,
        outline: `${scope} border-[var(--workflow-tone)]`,
        line: `${scope} bg-[var(--workflow-tone)]`,
        surface: `${scope} bg-[var(--workflow-soft)]`,
        rowMarker: `${scope} bg-[var(--workflow-tone)]`,
      },
    ]
  }),
) as Record<IndividualSignalState, VisualStyle>
