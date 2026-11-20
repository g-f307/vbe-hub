export function safeInternalReturnTo(value: string | undefined): string {
  if (!value || value.length > 2_000 || !value.startsWith('/') || value.startsWith('//') || /[\\\u0000-\u001f]/.test(value)) return '/'
  try {
    const path = decodeURIComponent(value.split('?')[0])
    if (path.startsWith('//') || path.includes('\\')) return '/'
  } catch { return '/' }
  return value
}
