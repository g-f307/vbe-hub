/**
 * Resolve a única configuração pública que o painel precisa para conversar
 * com a API. Ela é configurada pelo ambiente de implantação, nunca pela URL
 * ou por dados submetidos por uma pessoa usuária.
 */
export function resolveApiBaseUrl(rawValue = process.env.NEXT_PUBLIC_API_BASE_URL): string {
  const configuredValue = rawValue?.trim() || 'http://localhost:8000'

  let url: URL

  try {
    url = new URL(configuredValue)
  } catch {
    throw new Error('A URL pública da API é inválida.')
  }

  if (url.protocol !== 'http:' && url.protocol !== 'https:') {
    throw new Error('A URL pública da API deve usar HTTP ou HTTPS.')
  }

  if (url.username || url.password) {
    throw new Error('A URL pública da API não pode conter credenciais.')
  }

  if (url.search || url.hash) {
    throw new Error('A URL pública da API não pode conter parâmetros ou fragmentos.')
  }

  return url.toString().replace(/\/$/, '')
}
