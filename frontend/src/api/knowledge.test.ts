import { afterEach, describe, expect, it, vi } from 'vitest'

import { jsonResponse, requestUrl } from '../test/renderApp'
import { searchKnowledge } from './knowledge'

afterEach(() => vi.restoreAllMocks())

describe('searchKnowledge', () => {
  it('encodes the query, fixes the result limit, and uses shared credentials', async () => {
    let capturedInput: RequestInfo | URL | undefined
    let capturedInit: RequestInit | undefined
    vi.spyOn(globalThis, 'fetch').mockImplementation((input, init) => {
      capturedInput = input
      capturedInit = init
      return Promise.resolve(
        jsonResponse({
          query: 'VPN & payroll?',
          embedding_model: 'local-hash-v1',
          items: [],
        }),
      )
    })

    await searchKnowledge('VPN & payroll?')

    if (!capturedInput) throw new Error('Expected a knowledge search request.')
    const url = new URL(requestUrl(capturedInput), 'http://localhost')
    expect(url.pathname).toBe('/api/v1/knowledge/search')
    expect(url.searchParams.get('q')).toBe('VPN & payroll?')
    expect(url.searchParams.get('top_k')).toBe('5')
    expect(url.searchParams.has('category')).toBe(false)
    expect(capturedInit?.credentials).toBe('include')
  })

  it('rejects a malformed response instead of exposing it to the UI', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      jsonResponse({ status: 'ready' }),
    )

    await expect(searchKnowledge('VPN unavailable')).rejects.toThrow(
      'invalid knowledge response',
    )
  })
})
