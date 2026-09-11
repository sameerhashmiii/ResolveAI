import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import {
  jsonResponse,
  renderApp,
  requestUrl,
  userResponse,
} from '../test/renderApp'

afterEach(() => vi.restoreAllMocks())

describe('authentication', () => {
  it('starts a demo session without exposing credentials', async () => {
    const user = userEvent.setup()
    const fetchMock = vi
      .spyOn(globalThis, 'fetch')
      .mockImplementation((input) => {
        const url = requestUrl(input)
        if (url.endsWith('/auth/me'))
          return Promise.resolve(jsonResponse({}, 401))
        if (url.endsWith('/auth/demo'))
          return Promise.resolve(jsonResponse(userResponse))
        if (url.endsWith('/dashboard/overview')) {
          return Promise.resolve(
            jsonResponse({
              total_tickets: 0,
              open_tickets: 0,
              resolved_tickets: 0,
              escalated_tickets: 0,
              recent_tickets: [],
            }),
          )
        }
        return Promise.resolve(jsonResponse({ status: 'ready' }))
      })

    renderApp('/login')
    await user.click(await screen.findByRole('button', { name: 'Try Demo' }))

    await screen.findByRole('heading', { name: /service desk/i })
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/auth/demo',
      expect.objectContaining({ method: 'POST', credentials: 'include' }),
    )
    expect(screen.queryByText(/password.*demo/i)).not.toBeInTheDocument()
  })

  it('holds a protected route while authentication is loading', () => {
    vi.spyOn(globalThis, 'fetch').mockReturnValue(
      new Promise<Response>(() => undefined),
    )
    renderApp('/')
    expect(screen.getByRole('status')).toHaveTextContent(
      'Preparing your workspace',
    )
  })

  it('redirects an unauthenticated protected route to login', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(jsonResponse({}, 401))
    renderApp('/tickets')
    await waitFor(() =>
      expect(
        screen.getByRole('heading', { name: 'Sign in to ResolveAI' }),
      ).toBeInTheDocument(),
    )
  })
})
