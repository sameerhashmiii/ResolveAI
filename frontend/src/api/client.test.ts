import { afterEach, describe, expect, it, vi } from 'vitest'

import { createTicket } from './tickets'
import { jsonResponse } from '../test/renderApp'

afterEach(() => vi.restoreAllMocks())

describe('API mutation security', () => {
  it('uses cookie credentials and the in-memory CSRF token', async () => {
    const fetchMock = vi
      .spyOn(globalThis, 'fetch')
      .mockResolvedValue(jsonResponse({ id: '1' }, 201))
    await createTicket(
      {
        title: 'Printer offline',
        description: 'Third floor printer is unavailable.',
        requester_name: 'Taylor Reed',
      },
      'memory-token',
    )

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/tickets',
      expect.objectContaining({
        credentials: 'include',
        method: 'POST',
      }),
    )
    const request = fetchMock.mock.calls[0]?.[1]
    expect(new Headers(request?.headers).get('X-CSRF-Token')).toBe(
      'memory-token',
    )
  })
})
