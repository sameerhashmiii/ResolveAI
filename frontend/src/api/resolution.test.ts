import { afterEach, describe, expect, it, vi } from 'vitest'

import {
  decideRecommendation,
  escalateTicket,
  generateResponse,
  getLatestRecommendation,
  getLatestResponse,
  resolveTicket,
} from './resolution'
import { jsonResponse, requestUrl } from '../test/renderApp'

afterEach(() => vi.restoreAllMocks())

const recommendation = {
  id: 'rec-1',
  ticket_id: 'ticket-1',
  assessment_id: 'assessment-1',
  title: 'Reset VPN profile',
  original_instructions: 'Reset the VPN profile safely.',
  instructions: 'Reset the VPN profile safely.',
  action_type: 'troubleshoot',
  requires_approval: true,
  status: 'proposed',
  decided_by_id: null,
  decision_reason: null,
  decided_at: null,
  created_at: '2026-09-11T10:00:00Z',
  updated_at: '2026-09-11T10:00:00Z',
} as const

describe('resolution API', () => {
  it('guards malformed recommendation data', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(jsonResponse({ id: 'bad' }))
    await expect(getLatestRecommendation('ticket-1')).rejects.toThrow(
      'invalid recommendation response',
    )
  })

  it('guards malformed customer response data', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      jsonResponse({ id: 'response-1', status: 'sent' }),
    )
    await expect(getLatestResponse('ticket-1')).rejects.toThrow(
      'invalid customer response',
    )
  })

  it('sends a recommendation decision with reason and CSRF', async () => {
    let capturedInput: RequestInfo | URL | undefined
    let capturedInit: RequestInit | undefined
    vi.spyOn(globalThis, 'fetch').mockImplementation((input, init) => {
      capturedInput = input
      capturedInit = init
      return Promise.resolve(
        jsonResponse({ ...recommendation, status: 'approved' }),
      )
    })
    await decideRecommendation(
      'rec-1',
      { decision: 'approve', reason: 'Verified by support' },
      'csrf-token',
    )
    if (!capturedInput || typeof capturedInit?.body !== 'string')
      throw new Error('Expected a recommendation decision request.')
    expect(requestUrl(capturedInput)).toMatch(
      /\/recommendations\/rec-1\/decision$/,
    )
    expect(capturedInit.method).toBe('POST')
    expect(new Headers(capturedInit.headers).get('X-CSRF-Token')).toBe(
      'csrf-token',
    )
    expect(JSON.parse(capturedInit.body)).toEqual({
      decision: 'approve',
      reason: 'Verified by support',
    })
  })

  it('generates with no request body and resolves through the dedicated endpoint', async () => {
    const response = {
      id: 'response-1',
      ticket_id: 'ticket-1',
      assessment_id: 'assessment-1',
      recommendation_id: 'rec-1',
      generated_by: 'ai',
      provider: 'demo',
      model: null,
      mode: 'local_demo',
      draft_body: 'Hello Jordan',
      final_body: null,
      status: 'draft',
      created_by_id: 'user-1',
      approved_by_id: null,
      rejected_by_id: null,
      rejection_reason: null,
      approved_at: null,
      rejected_at: null,
      created_at: '2026-09-11T10:00:00Z',
      updated_at: '2026-09-11T10:00:00Z',
      approval_semantics: 'approval_only_not_sent',
    }
    const calls: Array<{ input: RequestInfo | URL; init?: RequestInit }> = []
    vi.spyOn(globalThis, 'fetch').mockImplementation((input, init) => {
      calls.push({ input, init })
      return Promise.resolve(
        calls.length === 1
          ? jsonResponse(response)
          : jsonResponse({ status: 'resolved' }),
      )
    })
    await generateResponse('ticket-1', 'csrf-token')
    await resolveTicket('ticket-1', 'response-1', 'VPN restored', 'csrf-token')
    expect(calls[0]?.init?.body).toBeUndefined()
    const resolveCall = calls[1]
    if (!resolveCall || typeof resolveCall.init?.body !== 'string')
      throw new Error('Expected a resolve request.')
    expect(requestUrl(resolveCall.input)).toMatch(
      /\/tickets\/ticket-1\/resolve$/,
    )
    expect(JSON.parse(resolveCall.init.body)).toEqual({
      response_id: 'response-1',
      resolution_summary: 'VPN restored',
    })
  })

  it('escalates through the dedicated endpoint with destination and reason', async () => {
    let capturedInput: RequestInfo | URL | undefined
    let capturedInit: RequestInit | undefined
    vi.spyOn(globalThis, 'fetch').mockImplementation((input, init) => {
      capturedInput = input
      capturedInit = init
      return Promise.resolve(jsonResponse({ status: 'escalated' }))
    })
    await escalateTicket(
      'ticket-1',
      'Network operations',
      'Gateway investigation required',
      'csrf-token',
    )
    if (!capturedInput || typeof capturedInit?.body !== 'string')
      throw new Error('Expected an escalation request.')
    expect(requestUrl(capturedInput)).toMatch(/\/tickets\/ticket-1\/escalate$/)
    expect(new Headers(capturedInit.headers).get('X-CSRF-Token')).toBe(
      'csrf-token',
    )
    expect(JSON.parse(capturedInit.body)).toEqual({
      destination: 'Network operations',
      reason: 'Gateway investigation required',
    })
  })
})
