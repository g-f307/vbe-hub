import { describe, expect, it } from 'vitest'

import { resolvePanelState } from './panel-state'

describe('resolvePanelState', () => {
  it('mantém a tela pronta como estado padrão', () => {
    expect(resolvePanelState(undefined)).toBe('ready')
  })

  it('aceita os estados demonstráveis sem depender de dados clínicos fictícios', () => {
    expect(resolvePanelState('carregando')).toBe('loading')
    expect(resolvePanelState('vazio')).toBe('empty')
    expect(resolvePanelState('indisponivel')).toBe('unavailable')
  })

  it('trata um parâmetro desconhecido como tela pronta', () => {
    expect(resolvePanelState('algo-inesperado')).toBe('ready')
  })
})
