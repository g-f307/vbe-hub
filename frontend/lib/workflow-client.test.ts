import { describe, expect, it } from 'vitest'

import { classifyWorkflowError, createOperationKey, reviewPayload, transitionPayload } from './workflow-client'

describe('workflow client payloads', () => {
  it('cria uma transição de encerramento com versão e motivo, sem identidade do ator', () => {
    const payload = transitionPayload({
      operationKey: 'transition-test-001',
      expectedVersion: 3,
      targetState: 'closed',
      reasonCode: 'insufficient_evidence',
      comment: 'As evidências sintéticas não sustentam continuidade.',
    })

    expect(payload).toEqual({
      operation_key: 'transition-test-001',
      expected_version: 3,
      target_state: 'closed',
      reason_code: 'insufficient_evidence',
      comment: 'As evidências sintéticas não sustentam continuidade.',
    })
    expect(payload).not.toHaveProperty('actor_id')
  })

  it('cria uma revisão corretiva com valor e motivo explícitos', () => {
    expect(reviewPayload({
      operationKey: 'review-test-001',
      expectedVersion: 2,
      targetType: 'grouping',
      targetId: '00000000-0000-0000-0000-000000000001',
      suggestionIdentityKey: 'a'.repeat(64),
      action: 'correct',
      correctedValue: { condition: 'Síndrome febril' },
      reasonCode: 'local_context',
      comment: 'A condição consolidada precisa ser ajustada.',
    })).toEqual({
      operation_key: 'review-test-001',
      expected_version: 2,
      target_type: 'grouping',
      target_id: '00000000-0000-0000-0000-000000000001',
      suggestion_identity_key: 'a'.repeat(64),
      action: 'correct',
      corrected_value: { condition: 'Síndrome febril' },
      reason_code: 'local_context',
      comment: 'A condição consolidada precisa ser ajustada.',
    })
  })
})

describe('workflow errors', () => {
  it('classifica conflito de versão e preserva a necessidade de recarregar', () => {
    expect(classifyWorkflowError(409, { code: 'workflow_version_conflict', current_version: 4 })).toMatchObject({
      kind: 'conflict',
      currentVersion: 4,
    })
  })

  it('classifica regra de validação sem mascarar seu código', () => {
    expect(classifyWorkflowError(422, { code: 'closure_reason_required' })).toMatchObject({
      kind: 'validation',
      code: 'closure_reason_required',
    })
  })
})

describe('createOperationKey', () => {
  it('gera chave segura distinta para cada submissão', () => {
    const first = createOperationKey('review')
    const second = createOperationKey('review')

    expect(first).toMatch(/^review-[A-Za-z0-9._@:-]+$/)
    expect(second).not.toBe(first)
  })
})
