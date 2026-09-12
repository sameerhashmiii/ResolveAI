import { screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import {
  jsonResponse,
  renderApp,
  requestUrl,
  userResponse,
} from '../test/renderApp'

afterEach(() => vi.restoreAllMocks())

describe('AnalyticsPage', () => {
  it('shows analyst-safe aggregate labels and provenance', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((input) => {
      const url = requestUrl(input)
      if (url.endsWith('/auth/me'))
        return Promise.resolve(jsonResponse(userResponse))
      if (url.endsWith('/analytics/overview'))
        return Promise.resolve(
          jsonResponse({
            synthetic: true,
            source: 'stored demo runs',
            methodology: 'aggregate snapshot',
            measured_at: '2026-09-11T00:00:00Z',
            dataset_version: 'tickets-v11',
            tickets: {
              total_tickets: 5,
              open_tickets: 1,
              resolved_tickets: 4,
              escalated_tickets: 0,
              resolution_rate: 0.8,
              sample_count: 5,
            },
            workflows: [
              {
                name: 'investigation',
                workflow_version: 'v11',
                completed: 4,
                failed: 1,
                total: 5,
                completion_rate: 0.8,
                median_duration_ms: 20,
              },
            ],
          }),
        )
      if (url.endsWith('/analytics/evaluation-summary'))
        return Promise.resolve(
          jsonResponse({
            synthetic: true,
            source: 'curated synthetic set',
            methodology: 'fixed runner',
            latest_run: null,
          }),
        )
      return Promise.resolve(jsonResponse({ status: 'ready' }))
    })
    renderApp('/analytics')

    expect(
      await screen.findByRole('heading', {
        name: 'Evaluation, with receipts.',
      }),
    ).toBeInTheDocument()
    expect(
      await screen.findByText('Workflow completion is not accuracy.'),
    ).toBeInTheDocument()
    expect(
      screen.getByText(/Denominator: 5 synthetic tickets/),
    ).toBeInTheDocument()
    expect(
      screen.getByRole('heading', { name: 'No completed evaluation yet.' }),
    ).toBeInTheDocument()
    expect(
      screen.queryByRole('link', { name: /Full observability/ }),
    ).not.toBeInTheDocument()
  })
})
