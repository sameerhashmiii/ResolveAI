import { apiRequest } from './client'
import type { AdminHealth } from './types'

export const getAdminHealth = (signal?: AbortSignal) =>
  apiRequest<AdminHealth>('/admin/health', { signal })
