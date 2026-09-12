import { screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import {
  jsonResponse,
  renderApp,
  requestUrl,
  userResponse,
} from '../test/renderApp'

afterEach(() => vi.restoreAllMocks())

const adminResponse = {
  ...userResponse,
  user: { ...userResponse.user, role: 'administrator' },
}

const overviewResponse = {
  synthetic: true,
  source: 'curated demo tickets',
  methodology: 'Snapshot aggregates over the demo dataset',
  measured_at: '2026-09-11T12:00:00Z',
  dataset_version: 'tickets-v9',
  tickets: {
    total_tickets: 20,
    open_tickets: 5,
    resolved_tickets: 12,
    escalated_tickets: 3,
    resolution_rate: 0.6,
    sample_count: 20,
  },
  workflows: [
    {
      name: 'triage',
      workflow_version: 'triage-v3',
      completed: 9,
      failed: 1,
      total: 10,
      completion_rate: 0.9,
      median_duration_ms: 450,
    },
  ],
}

const healthResponse = {
  status: 'healthy',
  service: 'resolveai-api',
  version: '0.9.0',
  environment: 'demo',
  checked_at: '2026-09-11T12:01:00Z',
  components: [{ name: 'database', status: 'up', latency_ms: 8 }],
}

function mockObservability(options?: {
  latestRun?: unknown
  degraded?: boolean
  errors?: boolean
}) {
  return vi.spyOn(globalThis, 'fetch').mockImplementation((input) => {
    const url = requestUrl(input)
    if (url.endsWith('/auth/me'))
      return Promise.resolve(jsonResponse(adminResponse))
    if (url.endsWith('/health/ready'))
      return Promise.resolve(jsonResponse({ status: 'ready' }))
    if (options?.errors) return Promise.resolve(jsonResponse({}, 503))
    if (url.endsWith('/analytics/overview'))
      return Promise.resolve(jsonResponse(overviewResponse))
    if (url.endsWith('/analytics/ai-performance')) {
      return Promise.resolve(
        jsonResponse({
          synthetic: true,
          source: 'curated evaluation set',
          methodology: 'Fixed aggregate benchmark',
          latest_run: options?.latestRun ?? null,
        }),
      )
    }
    if (url.endsWith('/admin/health')) {
      return Promise.resolve(
        jsonResponse(
          options?.degraded
            ? {
                ...healthResponse,
                status: 'degraded',
                components: [
                  { name: 'database', status: 'down', latency_ms: 900 },
                ],
              }
            : healthResponse,
        ),
      )
    }
    return Promise.resolve(jsonResponse({}))
  })
}

describe('AdminObservabilityPage', () => {
  it('shows admin navigation, synthetic context, denominators, and an honest empty evaluation', async () => {
    mockObservability()
    renderApp('/admin/observability')

    expect(
      await screen.findByRole('heading', { name: 'Evidence, not theater.' }),
    ).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Observability/ })).toHaveAttribute(
      'href',
      '/admin/observability',
    )
    expect(
      await screen.findAllByText('Denominator: 20 demo tickets'),
    ).toHaveLength(5)
    expect(
      screen.getAllByText('Synthetic demo measurement').length,
    ).toBeGreaterThan(3)
    expect(
      screen.getByText(/operational completion, not AI accuracy/i),
    ).toBeInTheDocument()
    expect(
      screen.getByRole('heading', { name: 'No completed evaluation yet.' }),
    ).toBeInTheDocument()
    expect(screen.getByText('tickets-v9')).toBeInTheDocument()
    expect(screen.getByText('triage-v3')).toBeInTheDocument()
  })

  it('renders bounded aggregate evaluation fields without case data', async () => {
    mockObservability({
      latestRun: {
        id: 'run-1',
        dataset_version: 'eval-v2',
        dataset_checksum: 'abc123',
        runner_version: 'runner-v1',
        workflow_version: 'workflow-v4',
        provider: 'local',
        model: null,
        sample_count: 40,
        metrics: {
          quality: { accuracy: 0.875, passed_count: 35 },
          hidden_case_output: 'private case content',
        },
        methodology: {
          scoring_threshold: 0.5,
          scoring_method: 'exact-match',
          prompt: 'hidden prompt',
        },
        completed_at: '2026-09-11T11:00:00Z',
      },
    })
    renderApp('/admin/observability')

    expect(await screen.findByText('87.5%')).toBeInTheDocument()
    expect(screen.getByText('35')).toBeInTheDocument()
    expect(screen.getByText('0.5')).toBeInTheDocument()
    expect(screen.queryByText('exact-match')).not.toBeInTheDocument()
    expect(screen.queryByText('private case content')).not.toBeInTheDocument()
    expect(screen.queryByText('hidden prompt')).not.toBeInTheDocument()
  })

  it('shows independent loading states', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((input) => {
      const url = requestUrl(input)
      if (url.endsWith('/auth/me'))
        return Promise.resolve(jsonResponse(adminResponse))
      if (url.endsWith('/health/ready'))
        return Promise.resolve(jsonResponse({ status: 'ready' }))
      return new Promise<Response>(() => undefined)
    })
    renderApp('/admin/observability')

    expect(
      await screen.findByText('Loading operations analytics...'),
    ).toBeInTheDocument()
    expect(screen.getByText('Loading ai performance...')).toBeInTheDocument()
    expect(screen.getByText('Loading service health...')).toBeInTheDocument()
  })

  it('shows recoverable API errors', async () => {
    mockObservability({ errors: true })
    renderApp('/admin/observability')

    expect(
      await screen.findByText('Operations analytics unavailable'),
    ).toBeInTheDocument()
    expect(screen.getByText('AI performance unavailable')).toBeInTheDocument()
    expect(screen.getByText('Service health unavailable')).toBeInTheDocument()
    expect(screen.getAllByRole('button', { name: 'Try again' })).toHaveLength(3)
  })

  it('calls out a degraded component state', async () => {
    mockObservability({ degraded: true })
    renderApp('/admin/observability')

    expect(await screen.findByText('Service is degraded.')).toBeInTheDocument()
    expect(screen.getByText('down')).toBeInTheDocument()
    expect(screen.getByText('900 ms')).toBeInTheDocument()
  })

  it('redirects non-administrators home without fetching admin data', async () => {
    const fetchMock = vi
      .spyOn(globalThis, 'fetch')
      .mockImplementation((input) => {
        const url = requestUrl(input)
        if (url.endsWith('/auth/me'))
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
    renderApp('/admin/observability')

    expect(
      await screen.findByRole('heading', {
        name: 'Service desk, at a glance.',
      }),
    ).toBeInTheDocument()
    expect(
      screen.queryByRole('link', { name: /Observability/ }),
    ).not.toBeInTheDocument()
    await waitFor(() => {
      expect(
        fetchMock.mock.calls.some(([input]) =>
          requestUrl(input).includes('/admin/health'),
        ),
      ).toBe(false)
    })
  })
})
