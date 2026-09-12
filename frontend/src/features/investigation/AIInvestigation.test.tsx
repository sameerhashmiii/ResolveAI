import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { Analysis, Investigation, TicketDetail } from '../../api/types'
import {
  jsonResponse,
  renderApp,
  requestUrl,
  userResponse,
} from '../../test/renderApp'

afterEach(() => vi.restoreAllMocks())

const ticket: TicketDetail = {
  id: 'ticket-investigation',
  ticket_number: 'RAI-1060',
  title: 'Intermittent DNS failures',
  description: 'Name resolution is failing for a user.',
  requester_name: 'Alex Rivera',
  category: 'network',
  priority: 'p2',
  status: 'new',
  assigned_to: null,
  created_by: userResponse.user,
  created_at: '2026-09-11T10:00:00Z',
  updated_at: '2026-09-11T10:00:00Z',
}

const analysis: Analysis = {
  id: 'analysis-investigation',
  ticket_id: ticket.id,
  status: 'completed',
  workflow_version: 'triage-v1',
  provider: 'resolveai-demo',
  model: null,
  mode: 'local_demo',
  category: 'network',
  category_confidence: 0.9,
  recommended_priority: 'p2',
  validated_priority: 'p2',
  entities: null,
  priority_factors: null,
  requires_manual_review: false,
  error_code: null,
  started_at: '2026-09-11T10:00:00Z',
  completed_at: '2026-09-11T10:00:01Z',
  duration_ms: 1000,
  created_at: '2026-09-11T10:00:00Z',
}

const investigation: Investigation = {
  id: 'investigation-1',
  ticket_id: ticket.id,
  analysis_id: analysis.id,
  requested_by_id: userResponse.user.id,
  status: 'completed',
  workflow_version: 'investigation-v1',
  reference_time: '2026-04-03T09:30:00Z',
  reference_basis: 'curated_demo_scenario',
  simulated_reference: true,
  planned_tools: [],
  limitations: [],
  error_code: null,
  started_at: '2026-09-11T10:02:00Z',
  completed_at: '2026-09-11T10:02:01Z',
  duration_ms: 450,
  created_at: '2026-09-11T10:02:00Z',
  steps: [
    {
      id: 'step-similar',
      step_key: 'internal_similar_key',
      step_order: 1,
      label: 'Compared resolved service requests',
      tool_name: 'search_similar_tickets',
      status: 'completed',
      source_count: 1,
      duration_ms: 40,
      sanitized_inputs: {},
      result: {
        items: [
          {
            source_id: 'RAI-0912',
            title: 'DNS lookups time out',
            similarity: 0.87,
            category: 'network',
            priority: 'p2',
            resolution: 'Flushed the stale resolver cache.',
            resolution_time_minutes: 28,
          },
        ],
      },
      created_at: '2026-09-11T10:02:00Z',
    },
    {
      id: 'step-status',
      step_key: 'internal_status_key',
      step_order: 2,
      label: 'Checked public service health',
      tool_name: 'get_service_status',
      status: 'completed',
      source_count: 1,
      duration_ms: 30,
      sanitized_inputs: {},
      result: {
        services: [
          {
            service: 'DNS resolver',
            status: 'degraded',
            source_id: 'status-dns-1',
            synthetic: true,
          },
        ],
      },
      created_at: '2026-09-11T10:02:00Z',
    },
    {
      id: 'step-telemetry',
      step_key: 'internal_telemetry_key',
      step_order: 3,
      label: 'Read resolver measurements',
      tool_name: 'query_telemetry',
      status: 'completed',
      source_count: 1,
      duration_ms: 50,
      sanitized_inputs: {},
      result: {
        records: [
          {
            metric: 'DNS latency',
            value: 842,
            unit: 'ms',
            source_id: 'telemetry-dns-1',
            synthetic: true,
          },
        ],
      },
      created_at: '2026-09-11T10:02:00Z',
    },
    {
      id: 'step-logs',
      step_key: 'internal_log_key',
      step_order: 4,
      label: 'Collected resolver logs',
      tool_name: 'search_logs',
      status: 'completed',
      source_count: 1,
      duration_ms: 55,
      sanitized_inputs: {},
      result: {
        records: [
          {
            message: 'Synthetic DNS timeout recorded',
            source_id: 'log-dns-1',
            synthetic: true,
          },
        ],
      },
      created_at: '2026-09-11T10:02:00Z',
    },
    {
      id: 'step-incident',
      step_key: 'internal_incident_key',
      step_order: 5,
      label: 'Found a related public incident',
      tool_name: 'lookup_related_incident',
      status: 'completed',
      source_count: 1,
      duration_ms: 35,
      sanitized_inputs: {},
      result: {
        related_incident: {
          title: 'Regional DNS degradation',
          status: 'monitoring',
          public_summary: 'Resolver latency was elevated.',
          source_id: 'INC-public-7',
          hidden_ground_truth: 'must not render',
        },
      },
      created_at: '2026-09-11T10:02:00Z',
    },
  ],
}

function setupFetch(
  latestAnalysis: Analysis | null,
  latestInvestigation: Investigation | null | Record<string, unknown>,
  activeInvestigation: Investigation = {
    ...investigation,
    id: 'investigation-new',
    status: 'running',
  },
) {
  return vi.spyOn(globalThis, 'fetch').mockImplementation((input) => {
    const url = requestUrl(input)
    if (url.endsWith('/auth/me'))
      return Promise.resolve(jsonResponse(userResponse))
    if (url.includes('/knowledge/search?'))
      return Promise.resolve(
        jsonResponse({
          query: ticket.title,
          embedding_model: 'local',
          items: [],
        }),
      )
    if (url.endsWith(`/tickets/${ticket.id}/analyses/latest`))
      return Promise.resolve(jsonResponse(latestAnalysis))
    if (url.endsWith(`/tickets/${ticket.id}/investigations/latest`))
      return Promise.resolve(jsonResponse(latestInvestigation))
    if (url.endsWith(`/tickets/${ticket.id}/assessments/latest`))
      return Promise.resolve(jsonResponse(null))
    if (url.endsWith(`/tickets/${ticket.id}/investigations`))
      return Promise.resolve(
        jsonResponse(
          { investigation_id: 'investigation-new', status: 'queued' },
          202,
        ),
      )
    if (url.endsWith('/investigations/investigation-new'))
      return Promise.resolve(jsonResponse(activeInvestigation))
    if (url.endsWith('/investigations/investigation-1/retry'))
      return Promise.resolve(
        jsonResponse(
          { investigation_id: 'investigation-new', status: 'queued' },
          202,
        ),
      )
    if (url.endsWith(`/tickets/${ticket.id}`))
      return Promise.resolve(jsonResponse(ticket))
    if (url.endsWith(`/tickets/${ticket.id}/events`))
      return Promise.resolve(jsonResponse([]))
    if (url.endsWith('/users')) return Promise.resolve(jsonResponse([]))
    return Promise.resolve(jsonResponse({ status: 'ready' }))
  })
}

function csrfHeader(init: RequestInit | undefined) {
  return new Headers(init?.headers).get('X-CSRF-Token')
}

describe('AI Investigation', () => {
  it('requires completed triage before offering the action', async () => {
    setupFetch(null, null)
    renderApp(`/tickets/${ticket.id}`)

    expect(
      await screen.findByRole('heading', {
        name: 'Structured triage required',
      }),
    ).toBeInTheDocument()
    expect(
      screen.queryByRole('button', { name: 'Start investigation' }),
    ).not.toBeInTheDocument()
  })

  it('starts with CSRF and polls only while active', async () => {
    const user = userEvent.setup()
    const fetchMock = setupFetch(analysis, null)
    renderApp(`/tickets/${ticket.id}`)

    await user.click(
      await screen.findByRole('button', { name: 'Start investigation' }),
    )
    expect(
      await screen.findByRole('heading', { name: 'Investigation running' }),
    ).toBeInTheDocument()
    const post = fetchMock.mock.calls.find(
      ([input, init]) =>
        requestUrl(input).endsWith(`/tickets/${ticket.id}/investigations`) &&
        init?.method === 'POST',
    )
    expect(csrfHeader(post?.[1])).toBe('csrf-test-token')
    await waitFor(
      () => {
        const polls = fetchMock.mock.calls.filter(([input]) =>
          requestUrl(input).endsWith('/investigations/investigation-new'),
        )
        expect(polls.length).toBeGreaterThan(1)
      },
      { timeout: 2200 },
    )
  })

  it('renders persisted labels and factual primary observations', async () => {
    setupFetch(analysis, investigation)
    renderApp(`/tickets/${ticket.id}`)

    const heading = await screen.findByRole('heading', {
      name: 'Evidence investigation',
    })
    const section = heading.closest('section')
    if (!section) throw new Error('Investigation section was not rendered.')
    expect(
      await within(section).findByText('Compared resolved service requests'),
    ).toBeInTheDocument()
    expect(
      within(section).queryByText('internal_similar_key'),
    ).not.toBeInTheDocument()
    expect(
      within(section).getByText('Flushed the stale resolver cache.'),
    ).toBeInTheDocument()
    expect(within(section).getByText('degraded')).toBeInTheDocument()
    expect(within(section).getByText('842')).toBeInTheDocument()
    expect(
      within(section).getByText('Synthetic DNS timeout recorded'),
    ).toBeInTheDocument()
    expect(
      within(section).getByText('Regional DNS degradation'),
    ).toBeInTheDocument()
    expect(within(section).getByText('status-dns-1')).toBeInTheDocument()
    expect(within(section).getByText('telemetry-dns-1')).toBeInTheDocument()
    expect(within(section).getByText('log-dns-1')).toBeInTheDocument()
    expect(within(section).getByText('INC-public-7')).toBeInTheDocument()
    expect(
      within(section).queryByText('must not render'),
    ).not.toBeInTheDocument()
    const disclaimer = within(section).getByText(
      'This investigation only collects observations and does not itself infer a root cause or recommend an action. The assessment is separate.',
    )
    expect(disclaimer).toBeInTheDocument()
    const observations = section.textContent?.replace(
      disclaimer.textContent ?? '',
      '',
    )
    expect(observations).not.toMatch(
      /root.?cause|recommend|confidence|show me why/i,
    )
  })

  it('handles malformed results and exposes a failed tool step', async () => {
    const statusStep = investigation.steps.find(
      (step) => step.id === 'step-status',
    )
    if (!statusStep) throw new Error('Status fixture step is missing.')
    const partial: Investigation = {
      ...investigation,
      steps: [
        {
          ...statusStep,
          status: 'failed',
          result: { services: ['malformed'] },
        },
      ],
    }
    setupFetch(analysis, partial)
    renderApp(`/tickets/${ticket.id}`)

    expect(
      await screen.findByText(
        'Limitation: this step did not complete successfully.',
      ),
    ).toBeInTheDocument()
    expect(
      screen.getByText('Observation data unavailable.'),
    ).toBeInTheDocument()
  })

  it('retries a failed investigation with CSRF', async () => {
    const user = userEvent.setup()
    const failed: Investigation = {
      ...investigation,
      status: 'failed',
    }
    const fetchMock = setupFetch(analysis, failed)
    renderApp(`/tickets/${ticket.id}`)

    expect(
      await screen.findByRole('heading', {
        name: 'Investigation failed safely',
      }),
    ).toBeInTheDocument()
    await user.click(
      screen.getByRole('button', { name: 'Retry investigation' }),
    )
    expect(
      await screen.findByRole('heading', { name: 'Investigation running' }),
    ).toBeInTheDocument()
    const retry = fetchMock.mock.calls.find(([input]) =>
      requestUrl(input).endsWith('/investigations/investigation-1/retry'),
    )
    expect(retry?.[1]?.method).toBe('POST')
    expect(csrfHeader(retry?.[1])).toBe('csrf-test-token')
  })
})
