import { screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import {
  jsonResponse,
  renderApp,
  requestUrl,
  userResponse,
} from '../test/renderApp'

afterEach(() => vi.restoreAllMocks())

function mockDashboard(recentTickets: unknown[] = []) {
  vi.spyOn(globalThis, 'fetch').mockImplementation((input) => {
    const url = requestUrl(input)
    if (url.endsWith('/auth/me'))
      return Promise.resolve(jsonResponse(userResponse))
    if (url.endsWith('/dashboard/overview')) {
      return Promise.resolve(
        jsonResponse({
          total_tickets: 19,
          open_tickets: 7,
          resolved_tickets: 10,
          escalated_tickets: 2,
          recent_tickets: recentTickets,
        }),
      )
    }
    return Promise.resolve(jsonResponse({ status: 'ready' }))
  })
}

describe('DashboardPage', () => {
  it('renders Phase 2 metrics from the API', async () => {
    mockDashboard()
    renderApp('/workspace')

    await screen.findByText('19')
    expect(screen.getByText('Total tickets')).toBeInTheDocument()
    expect(screen.getByText('Open')).toBeInTheDocument()
    expect(screen.getByText('Resolved')).toBeInTheDocument()
    expect(screen.getByText('Escalated')).toBeInTheDocument()
    expect(
      screen.getByLabelText('Platform health: Operational'),
    ).toBeInTheDocument()
    expect(screen.getByLabelText('Demo environment notice')).toHaveTextContent(
      'are synthetic',
    )
  })

  it('shows an honest empty queue state', async () => {
    mockDashboard()
    renderApp('/workspace')
    expect(
      await screen.findByRole('heading', { name: 'Your queue is ready.' }),
    ).toBeInTheDocument()
    expect(
      screen.getByRole('link', { name: 'Create first ticket' }),
    ).toHaveAttribute('href', '/tickets/new')
  })
})
