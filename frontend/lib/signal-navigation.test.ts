import { describe, expect, it } from 'vitest'
import { evidenceHref, resolveSignalNavigation, resolveSignalTab } from './signal-navigation'

describe('navegação contextual do sinal', () => {
  it('preserva aba e cursor na consulta de incorporado e no retorno à fila', () => {
    const queue = '/?state=triage&source_kind=media&view=list&cursor=page-two&query=febre'
    const href = evidenceHref('evidence', 'head', 'evidence', queue)
    const back = new URL(href, 'http://localhost').searchParams.get('returnTo')!
    expect(back).toContain('tab=evidence')
    expect(resolveSignalNavigation(back, 'head')).toEqual({ queueHref: queue, headHref: back })
  })

  it('reconhece as URLs antigas e abre os candidatos no novo modal', () => {
    expect(resolveSignalTab('related')).toEqual({ tab: 'evidence', openCandidates: true })
    expect(resolveSignalTab('evidence')).toEqual({ tab: 'evidence', openCandidates: false })
    expect(resolveSignalTab('overview')).toEqual({ tab: 'overview', openCandidates: false })
  })

  it('rejeita destinos externos inclusive codificações ambíguas e barras invertidas', () => {
    for (const url of ['//evil.example', '/\\evil.example', '/%2f%2fevil.example', 'https://evil.example']) {
      expect(resolveSignalNavigation(url, null).queueHref).toBe('/')
    }
  })

  it('acesso direto ao incorporado aponta para sua cabeça real sem inventar retorno', () => {
    expect(resolveSignalNavigation('/', 'head')).toEqual({ queueHref: '/', headHref: '/sinais/head?tab=overview&returnTo=%2F' })
  })
})
