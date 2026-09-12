import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { Analysis, TicketDetail } from '../api/types'
import {
  jsonResponse,
  renderApp,
  requestUrl,
  userResponse,
} from '../test/renderApp'

afterEach(() => vi.restoreAllMocks())

const ticket: TicketDetail = {
  id: 'ticket-42',
  ticket_number: 'RAI-1042',
  title: 'VPN access unavailable',
  description: 'Jordan cannot connect to the VPN from the London office.',
  requester_name: 'Jordan Lee',
  requester_department: 'Finance',
  location: 'London',
  device: 'Laptop-17',
  application: 'Secure VPN',
  category: null,
  priority: null,
  priority_overridden: false,
  priority_override_reason: null,
  status: 'new',
  assigned_to: null,
  created_by: userResponse.user,
  created_at: '2026-09-11T10:00:00Z',
  updated_at: '2026-09-11T10:00:00Z',
}

const completedAnalysis: Analysis = {
  id: 'analysis-1',
  ticket_id: ticket.id,
  status: 'completed',
  workflow_version: 'triage-v1',
  provider: 'resolveai-demo',
  model: null,
  mode: 'local_demo',
  category: 'vpn',
  category_confidence: 0.92,
  recommended_priority: 'p2',
  validated_priority: 'p2',
  entities: {
    user: 'Jordan Lee',
    location: 'London',
    application: 'Secure VPN',
    device: 'Laptop-17',
    issue_type: 'Access failure',
    affected_scope: 'Single user',
    urgency: 'High',
  },
  priority_factors: { affected_users: 1, business_impact: 'High' },
  requires_manual_review: false,
  error_code: null,
  started_at: '2026-09-11T10:01:00Z',
  completed_at: '2026-09-11T10:01:01Z',
  duration_ms: 1250,
  created_at: '2026-09-11T10:01:00Z',
}

function setupFetch(
  analysis: Analysis | null,
  options: { ticket?: TicketDetail; activeAnalysis?: Analysis } = {},
) {
  let currentTicket = options.ticket ?? ticket
  return vi
    .spyOn(globalThis, 'fetch')
    .mockImplementation((input, init = {}) => {
      const url = requestUrl(input)
      if (url.endsWith('/auth/me'))
        return Promise.resolve(jsonResponse(userResponse))
      if (url.includes('/knowledge/search?'))
        return Promise.resolve(
          jsonResponse({
            query: 'VPN access unavailable',
            embedding_model: 'local-hash-v1',
            items: [],
          }),
        )
      if (url.endsWith(`/tickets/${ticket.id}/analyses/latest`))
        return Promise.resolve(jsonResponse(analysis))
      if (url.endsWith(`/tickets/${ticket.id}/analyses`))
        return Promise.resolve(
          jsonResponse({ analysis_id: 'analysis-new', status: 'queued' }, 202),
        )
      if (url.endsWith(`/tickets/${ticket.id}/investigations/latest`))
        return Promise.resolve(jsonResponse(null))
      if (url.endsWith(`/tickets/${ticket.id}/assessments/latest`))
        return Promise.resolve(jsonResponse(null))
      if (url.endsWith('/analyses/analysis-new'))
        return Promise.resolve(
          jsonResponse(
            options.activeAnalysis ?? {
              ...completedAnalysis,
              id: 'analysis-new',
              status: 'queued',
            },
          ),
        )
      if (url.endsWith('/analyses/analysis-1/retry'))
        return Promise.resolve(
          jsonResponse({ analysis_id: 'analysis-new', status: 'queued' }, 202),
        )
      if (url.endsWith(`/tickets/${ticket.id}/priority-override`)) {
        const body = requestBody(init)
        if (
          typeof body !== 'object' ||
          body === null ||
          !('priority' in body) ||
          typeof body.priority !== 'string' ||
          !('reason' in body) ||
          typeof body.reason !== 'string'
        )
          throw new Error('Invalid priority override test request.')
        currentTicket = {
          ...currentTicket,
          priority: body.priority,
          priority_overridden: true,
          priority_override_reason: body.reason,
        }
        return Promise.resolve(jsonResponse(currentTicket))
      }
      if (url.endsWith(`/tickets/${ticket.id}`))
        return Promise.resolve(jsonResponse(currentTicket))
      if (url.endsWith(`/tickets/${ticket.id}/events`))
        return Promise.resolve(jsonResponse([]))
      if (url.endsWith('/users')) return Promise.resolve(jsonResponse([]))
      if (url.includes('/tickets?'))
        return Promise.resolve(
          jsonResponse({
            items: [currentTicket],
            page: 1,
            page_size: 20,
            total: 1,
            has_next: false,
          }),
        )
      return Promise.resolve(jsonResponse({ status: 'ready' }))
    })
}

function csrfHeader(init: RequestInit | undefined) {
  return new Headers(init?.headers).get('X-CSRF-Token')
}

function requestBody(init: RequestInit | undefined): unknown {
  if (typeof init?.body !== 'string') {
    throw new Error('Expected a JSON request body in this test.')
  }
  return JSON.parse(init.body) as unknown
}

describe('TicketDetailPage AI triage', () => {
  it('requests a new analysis with CSRF and transitions to queued status', async () => {
    const user = userEvent.setup()
    const fetchMock = setupFetch(null)
    renderApp(`/tickets/${ticket.id}`)

    await user.click(
      await screen.findByRole('button', { name: 'Analyze ticket' }),
    )

    expect(
      await screen.findByRole('heading', { name: 'Analysis queued' }),
    ).toBeInTheDocument()
    const post = fetchMock.mock.calls.find(
      ([input, init]) =>
        requestUrl(input).endsWith(`/tickets/${ticket.id}/analyses`) &&
        init?.method === 'POST',
    )
    expect(csrfHeader(post?.[1])).toBe('csrf-test-token')
    expect(
      fetchMock.mock.calls.some(([input]) =>
        requestUrl(input).endsWith('/analyses/analysis-new'),
      ),
    ).toBe(true)
  })

  it('renders completed deterministic triage without a root-cause claim', async () => {
    setupFetch(completedAnalysis)
    renderApp(`/tickets/${ticket.id}`)

    const heading = await screen.findByRole('heading', {
      name: 'AI Ticket Triage',
    })
    const triage = heading.closest('section')
    if (!triage) throw new Error('Triage section was not rendered.')
    expect(
      await within(triage).findByText('VPN / Remote Access'),
    ).toBeInTheDocument()
    expect(within(triage).getByText('92% confidence')).toBeInTheDocument()
    expect(within(triage).getByText('P2')).toBeInTheDocument()
    expect(within(triage).getByText('Jordan Lee')).toBeInTheDocument()
    expect(within(triage).getByText('London')).toBeInTheDocument()
    expect(within(triage).getByText('Secure VPN')).toBeInTheDocument()
    expect(within(triage).getByText('Laptop-17')).toBeInTheDocument()
    expect(
      within(triage).getByText('Deterministic demo provider'),
    ).toBeInTheDocument()
    expect(
      within(triage).queryByText(/root cause identified/i),
    ).not.toBeInTheDocument()
  })

  it('shows a bounded active status and polls only that status', async () => {
    const active = { ...completedAnalysis, status: 'running' as const }
    const fetchMock = setupFetch(active)
    renderApp(`/tickets/${ticket.id}`)

    expect(
      await screen.findByRole('heading', { name: 'Analysis running' }),
    ).toBeInTheDocument()
    expect(screen.getByText(/refreshes automatically/i)).toBeInTheDocument()
    expect(
      screen.queryByText(/step 1|step 2|percent complete/i),
    ).not.toBeInTheDocument()
    await waitFor(
      () => {
        const polls = fetchMock.mock.calls.filter(([input]) =>
          requestUrl(input).endsWith(`/tickets/${ticket.id}/analyses/latest`),
        )
        expect(polls.length).toBeGreaterThan(1)
      },
      { timeout: 2200 },
    )
  })

  it('maps a safe failure code and retries with CSRF', async () => {
    const user = userEvent.setup()
    const failed: Analysis = {
      ...completedAnalysis,
      status: 'failed',
      error_code: 'invalid_provider_response',
    }
    const fetchMock = setupFetch(failed)
    renderApp(`/tickets/${ticket.id}`)

    expect(
      await screen.findByText(
        'The provider returned an unusable structured response.',
      ),
    ).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Retry analysis' }))

    await screen.findByRole('heading', { name: 'Analysis queued' })
    const retry = fetchMock.mock.calls.find(([input]) =>
      requestUrl(input).endsWith('/analyses/analysis-1/retry'),
    )
    expect(retry?.[1]?.method).toBe('POST')
    expect(csrfHeader(retry?.[1])).toBe('csrf-test-token')
  })

  it('validates and applies a human priority override with CSRF', async () => {
    const user = userEvent.setup()
    const fetchMock = setupFetch(completedAnalysis)
    renderApp(`/tickets/${ticket.id}`)

    await screen.findByRole('heading', { name: 'Priority override' })
    await user.selectOptions(screen.getByLabelText('Priority'), 'p1')
    await user.click(screen.getByRole('button', { name: 'Apply override' }))
    expect(
      screen.getByText(
        'Provide at least 5 characters explaining the override.',
      ),
    ).toBeInTheDocument()
    expect(
      fetchMock.mock.calls.some(([input]) =>
        requestUrl(input).endsWith(`/tickets/${ticket.id}/priority-override`),
      ),
    ).toBe(false)

    await user.type(
      screen.getByLabelText('Reason'),
      'Finance payroll is blocked',
    )
    await user.click(screen.getByRole('button', { name: 'Apply override' }))

    expect(await screen.findAllByText('Human override')).not.toHaveLength(0)
    expect(screen.getAllByText('Finance payroll is blocked')).not.toHaveLength(
      0,
    )
    const request = fetchMock.mock.calls.find(([input]) =>
      requestUrl(input).endsWith(`/tickets/${ticket.id}/priority-override`),
    )
    expect(csrfHeader(request?.[1])).toBe('csrf-test-token')
    expect(requestBody(request?.[1])).toEqual({
      priority: 'p1',
      reason: 'Finance payroll is blocked',
    })
    await waitFor(() => {
      expect(
        fetchMock.mock.calls.filter(([input]) =>
          requestUrl(input).endsWith(`/tickets/${ticket.id}/events`),
        ).length,
      ).toBeGreaterThan(1)
    })
  })
})
