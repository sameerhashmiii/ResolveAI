import { apiRequest } from './client'
import type { DashboardOverview } from './types'

export const getDashboardOverview = (signal?: AbortSignal) =>
  apiRequest<DashboardOverview>('/dashboard/overview', { signal })
