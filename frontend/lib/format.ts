export const NOW_ISO = '2026-10-07T14:32:00-04:00'

const MONTHS = ['jan.', 'fev.', 'mar.', 'abr.', 'maio', 'jun.', 'jul.', 'ago.', 'set.', 'out.', 'nov.', 'dez.']
const MANAUS_OFFSET_MS = -4 * 60 * 60 * 1000

function toManaus(iso: string) {
  const d = new Date(new Date(iso).getTime() + MANAUS_OFFSET_MS)
  return {
    day: d.getUTCDate(),
    month: d.getUTCMonth(),
    year: d.getUTCFullYear(),
    hours: String(d.getUTCHours()).padStart(2, '0'),
    minutes: String(d.getUTCMinutes()).padStart(2, '0'),
  }
}

export function formatDate(iso: string) {
  const d = toManaus(iso)
  return `${d.day} ${MONTHS[d.month]} ${d.year}`
}

export function formatShortDate(iso: string) {
  const d = toManaus(iso)
  return `${d.day} ${MONTHS[d.month]}`
}

export function formatDateTime(iso: string) {
  const d = toManaus(iso)
  return `${d.day} ${MONTHS[d.month]} ${d.year}, ${d.hours}:${d.minutes}`
}

export function formatTime(iso: string) {
  const d = toManaus(iso)
  return `${d.hours}:${d.minutes}`
}

export function formatPeriod(startIso: string | null, endIso: string | null) {
  if (!startIso && !endIso) return 'Não informado'
  if (!startIso) return `Até ${formatDate(endIso!)}`
  if (!endIso) return `A partir de ${formatDate(startIso)}`
  const s = toManaus(startIso)
  const e = toManaus(endIso)
  if (s.month === e.month && s.year === e.year) {
    return s.day === e.day
      ? `${s.day} ${MONTHS[s.month]} ${s.year}`
      : `${s.day}–${e.day} ${MONTHS[s.month]} ${s.year}`
  }
  return `${s.day} ${MONTHS[s.month]}–${e.day} ${MONTHS[e.month]} ${e.year}`
}

export function minutesSince(iso: string, nowIso: string = NOW_ISO) {
  return Math.max(0, Math.round((new Date(nowIso).getTime() - new Date(iso).getTime()) / 60000))
}

export function formatRelative(iso: string, nowIso: string = NOW_ISO) {
  const minutes = minutesSince(iso, nowIso)
  if (minutes < 1) return 'agora'
  if (minutes < 60) return `há ${minutes} min`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `há ${hours} h`
  const days = Math.floor(hours / 24)
  return days === 1 ? 'há 1 dia' : `há ${days} dias`
}

export function formatPercent(value: number) {
  return `${Math.round(value * 100)}%`
}
