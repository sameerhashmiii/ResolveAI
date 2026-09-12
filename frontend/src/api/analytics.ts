import { apiRequest } from './client'
import type { AiPerformanceAnalytics, AnalyticsOverview } from './types'

export const getAnalyticsOverview = (signal?: AbortSignal) =>
  apiRequest<AnalyticsOverview>('/analytics/overview', { signal })

export const getAiPerformance = (signal?: AbortSignal) =>
  apiRequest<AiPerformanceAnalytics>('/analytics/ai-performance', { signal })

export const getEvaluationSummary = (signal?: AbortSignal) =>
  apiRequest<AiPerformanceAnalytics>('/analytics/evaluation-summary', {
    signal,
  })
