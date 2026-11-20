import { describe, expect, it } from 'vitest'
import { emptyInformation, formatInformationDate, informationForSignal, mapSignalInformation } from './signal-information'

describe('informações operacionais', () => {
  it('preserva ausência e não converte confiança de IA em confidencialidade', () => {
    const info = informationForSignal({ technicalSheet: { confidence: 0.99, disease_or_condition: 'Dengue (suspeita)' }, provenance: { collectedAt: '2026-11-20T08:00:00Z' } })
    expect(info.etiology).toBe('Dengue (suspeita)')
    expect(info.confidentiality).toBeNull()
    expect(info.signal_type).toBeNull()
    expect(info.notified_at).toBeNull()
  })
  it('mantém datas sem hora e usa o fuso de Manaus para timestamps', () => {
    expect(formatInformationDate('2026-11-14')).toBe('14/11/2026')
    expect(formatInformationDate('2026-11-20T12:00:00Z')).toBe('20/11/2026, 08:00')
    expect(formatInformationDate(null)).toBe('Não informado')
  })
  it('valida os novos campos recebidos da API', () => {
    expect(mapSignalInformation({ ...emptyInformation(), hazard_general: 'Arbovirose', tags: ['dengue'] })).toMatchObject({ hazard_general: 'Arbovirose', tags: ['dengue'] })
    expect(() => mapSignalInformation({ ...emptyInformation(), tags: [42] })).toThrow()
  })
})
