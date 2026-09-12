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

function setupFetch() {
  return vi.spyOn(globalThis, 'fetch').mockImplementation((input) => {
    const url = requestUrl(input)
    if (url.endsWith('/auth/me'))
      return Promise.resolve(jsonResponse(userResponse))
    if (url.endsWith('/tickets') && !url.includes('?')) {
      return Promise.resolve(
        jsonResponse({ id: 'ticket-42', ticket_number: 'RAI-1000' }, 201),
      )
    }
    if (url.endsWith('/tickets/ticket-42')) {
      return Promise.resolve(
        jsonResponse({
          id: 'ticket-42',
          ticket_number: 'RAI-1000',
          title: 'VPN access unavailable',
          description: 'Cannot connect from home.',
          requester_name: 'Sam Lee',
          category: null,
          priority: null,
          priority_overridden: false,
          priority_override_reason: null,
          status: 'new',
          assigned_to: null,
          created_by: userResponse.user,
          created_at: '2026-09-11T10:00:00Z',
          updated_at: '2026-09-11T10:00:00Z',
        }),
      )
    }
    if (url.endsWith('/tickets/ticket-42/events'))
      return Promise.resolve(jsonResponse([]))
    if (url.endsWith('/tickets/ticket-42/analyses/latest'))
      return Promise.resolve(jsonResponse(null))
    if (url.endsWith('/users')) return Promise.resolve(jsonResponse([]))
    if (url.includes('/knowledge/search?'))
      return Promise.resolve(
        jsonResponse({
          query: 'VPN access unavailable',
          embedding_model: 'local-hash-v1',
          items: [],
        }),
      )
    return Promise.resolve(jsonResponse({ status: 'ready' }))
  })
}

describe('CreateTicketPage', () => {
  it('validates required intake fields', async () => {
    const user = userEvent.setup()
    setupFetch()
    renderApp('/tickets/new')

    await user.click(
      await screen.findByRole('button', { name: 'Create ticket' }),
    )
    expect(screen.getAllByText('This field is required.')).toHaveLength(3)
    expect(screen.getByLabelText(/Title/)).toHaveFocus()
  })

  it('prefills a validated scenario without starting a workflow', async () => {
    setupFetch()
    renderApp('/tickets/new?scenario=dallas-vpn-payrollpro-dns')

    expect(await screen.findByLabelText(/Title/)).toHaveValue(
      'VPN works, PayrollPro does not',
    )
    expect(screen.getByLabelText('Location')).toHaveValue('Dallas')
    expect(screen.getByLabelText('Application')).toHaveValue('PayrollPro')
    expect(
      screen.getByText(/no workflow starts automatically/i),
    ).toBeInTheDocument()
  })

  it('submits with CSRF and navigates to the created ticket', async () => {
    const user = userEvent.setup()
    const fetchMock = setupFetch()
    renderApp('/tickets/new')

    await user.type(
      await screen.findByLabelText(/Title/),
      'VPN access unavailable',
    )
    await user.type(
      screen.getByLabelText(/Description/),
      'Cannot connect from home.',
    )
    await user.type(screen.getByLabelText(/Requester name/), 'Sam Lee')
    await user.click(screen.getByRole('button', { name: 'Create ticket' }))

    await screen.findByRole('heading', { name: 'VPN access unavailable' })
    await waitFor(() => {
      const call = fetchMock.mock.calls.find(([input]) =>
        requestUrl(input).endsWith('/tickets'),
      )
      expect(call?.[1]).toEqual(
        expect.objectContaining({ method: 'POST', credentials: 'include' }),
      )
      expect(new Headers(call?.[1]?.headers).get('X-CSRF-Token')).toBe(
        'csrf-test-token',
      )
    })
  })
})
