export function safeInternalReturnTo(value: string | undefined): string {
  if (!value || value.length > 2_000 || !value.startsWith('/') || value.startsWith('//')) return '/'
  return value
}
