import { requestSignalApiJson, SignalReadError } from './signal-read'

export type GeographicArea = {
  key: string
  municipality: string
  district: string
  signals: number
  sourceCounts: { media: number; community: number; total: number }
  workflowStates: Record<string, number>
  priorityBands: Record<string, number>
  topCondition: { label: string; count: number } | null
}

export type GeographicSummary = {
  datasetKind: 'synthetic'
  datasetIdentity: string
  window: { start: string | null; end: string | null }
  updatedAt: string | null
  totals: { signals: number; mappedSignals: number; unmappedSignals: number; areas: number }
  areas: GeographicArea[]
}

export async function getGeographicSummary(): Promise<GeographicSummary> {
  return mapGeographicSummary(await requestSignalApiJson('/signals/geographic-summary'))
}

export function mapGeographicSummary(value: unknown): GeographicSummary {
  if (!isRecord(value) || value.dataset_kind !== 'synthetic' || typeof value.dataset_identity !== 'string') {
    throw invalidSummary()
  }
  const window = requireRecord(value.window)
  const totals = requireRecord(value.totals)
  if (!Array.isArray(value.areas)) throw invalidSummary()

  return {
    datasetKind: 'synthetic',
    datasetIdentity: value.dataset_identity,
    window: {
      start: nullableString(window.start),
      end: nullableString(window.end),
    },
    updatedAt: nullableString(value.updated_at),
    totals: {
      signals: requireCount(totals.signals),
      mappedSignals: requireCount(totals.mapped_signals),
      unmappedSignals: requireCount(totals.unmapped_signals),
      areas: requireCount(totals.areas),
    },
    areas: value.areas.map(mapArea),
  }
}

function mapArea(value: unknown): GeographicArea {
  const area = requireRecord(value)
  const sources = requireRecord(area.source_counts)
  const topCondition = area.top_condition === null ? null : requireRecord(area.top_condition)
  return {
    key: requireString(area.key),
    municipality: requireString(area.municipality),
    district: requireString(area.district),
    signals: requireCount(area.signals),
    sourceCounts: {
      media: requireCount(sources.media),
      community: requireCount(sources.community),
      total: requireCount(sources.total),
    },
    workflowStates: requireCounts(area.workflow_states),
    priorityBands: requireCounts(area.priority_bands),
    topCondition: topCondition
      ? { label: requireString(topCondition.label), count: requireCount(topCondition.count) }
      : null,
  }
}

function requireCounts(value: unknown): Record<string, number> {
  const record = requireRecord(value)
  return Object.fromEntries(Object.entries(record).map(([key, count]) => [key, requireCount(count)]))
}

function requireRecord(value: unknown): Record<string, unknown> {
  if (!isRecord(value)) throw invalidSummary()
  return value
}

function requireString(value: unknown): string {
  if (typeof value !== 'string' || !value.trim()) throw invalidSummary()
  return value
}

function nullableString(value: unknown): string | null {
  if (value === null) return null
  return requireString(value)
}

function requireCount(value: unknown): number {
  if (!Number.isInteger(value) || Number(value) < 0) throw invalidSummary()
  return Number(value)
}

function invalidSummary(): SignalReadError {
  return new SignalReadError('A API retornou um resumo territorial em formato inválido.', 'invalid-response')
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}
