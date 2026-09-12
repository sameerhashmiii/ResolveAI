import { afterEach, describe, expect, it, vi } from 'vitest'

import { jsonResponse, requestUrl } from '../test/renderApp'
import { getAdminHealth } from './adminHealth'
import {
  getAiPerformance,
  getAnalyticsOverview,
  getEvaluationSummary,
} from './analytics'

afterEach(() => vi.restoreAllMocks())

describe('observability APIs', () => {
  it('requests all endpoints through the authenticated shared client', async () => {
    const requests: Array<{ input: RequestInfo | URL; init?: RequestInit }> = []
    vi.spyOn(globalThis, 'fetch').mockImplementation((input, init) => {
      requests.push({ input, init })
      return Promise.resolve(jsonResponse({}))
    })

    await Promise.all([
      getAnalyticsOverview(),
      getAiPerformance(),
      getEvaluationSummary(),
      getAdminHealth(),
    ])

    expect(requests.map(({ input }) => requestUrl(input))).toEqual([
      '/api/v1/analytics/overview',
      '/api/v1/analytics/ai-performance',
      '/api/v1/analytics/evaluation-summary',
      '/api/v1/admin/health',
    ])
    requests.forEach(({ init }) => {
      expect(init).toEqual(expect.objectContaining({ credentials: 'include' }))
    })
  })
})
