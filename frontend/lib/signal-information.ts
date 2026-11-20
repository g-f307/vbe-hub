export type SignalInformation = {
  confidentiality: string | null
  signal_type: string | null
  etiology: string | null
  hazard_general: string | null
  hazard_specific: string | null
  tags: string[]
  signal_date: string | null
  detected_at: string | null
  notified_at: string | null
  origins: Record<string, string>
}

export function mapSignalInformation(
  value: unknown,
): SignalInformation | undefined {
  if (value === undefined || value === null) return undefined
  if (typeof value !== 'object' || Array.isArray(value))
    throw new Error('Informações do sinal inválidas.')
  const row = value as Record<string, unknown>
  const result = emptyInformation()
  for (const key of [
    'confidentiality',
    'signal_type',
    'etiology',
    'hazard_general',
    'hazard_specific',
    'signal_date',
    'detected_at',
    'notified_at',
  ] as const) {
    if (
      row[key] !== undefined &&
      row[key] !== null &&
      typeof row[key] !== 'string'
    )
      throw new Error('Campo do sinal inválido.')
    result[key] = typeof row[key] === 'string' ? row[key] : null
  }
  if (
    !Array.isArray(row.tags) ||
    !row.tags.every((tag) => typeof tag === 'string')
  )
    throw new Error('Etiquetas inválidas.')
  result.tags = row.tags
  if (row.origins && typeof row.origins === 'object') {
    result.origins = Object.fromEntries(
      Object.entries(row.origins).filter(
        (entry): entry is [string, string] => typeof entry[1] === 'string',
      ),
    )
  }
  return result
}

export function emptyInformation(): SignalInformation {
  return {
    confidentiality: null,
    signal_type: null,
    etiology: null,
    hazard_general: null,
    hazard_specific: null,
    tags: [],
    signal_date: null,
    detected_at: null,
    notified_at: null,
    origins: {},
  }
}

export function informationForSignal(signal: {
  information?: SignalInformation
  technicalSheet: Record<string, unknown> | null
  provenance: { collectedAt: string }
}): SignalInformation {
  if (signal.information) return signal.information
  const sheet = signal.technicalSheet
  const temporal = sheet?.temporal
  return {
    ...emptyInformation(),
    etiology:
      typeof sheet?.disease_or_condition === 'string'
        ? sheet.disease_or_condition
        : null,
    signal_date:
      temporal &&
      typeof temporal === 'object' &&
      'start' in temporal &&
      typeof temporal.start === 'string'
        ? temporal.start
        : null,
    detected_at: signal.provenance.collectedAt,
  }
}

export function formatInformationDate(value: string | null): string {
  if (!value) return 'Não informado'
  // A date without a time is a calendar date, not midnight UTC.
  if (/^\d{4}-\d{2}-\d{2}$/.test(value)) {
    const [year, month, day] = value.split('-')
    return `${day}/${month}/${year}`
  }
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return 'Não informado'
  return new Intl.DateTimeFormat('pt-BR', {
    dateStyle: 'short',
    timeStyle: 'short',
    timeZone: 'America/Manaus',
  }).format(date)
}
