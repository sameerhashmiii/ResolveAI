import { apiRequest } from './client'
import type {
  Analysis,
  AnalysisAccepted,
  PriorityOverrideInput,
  TicketDetail,
} from './types'

export const createAnalysis = (ticketId: string, csrfToken: string) =>
  apiRequest<AnalysisAccepted>(
    `/tickets/${encodeURIComponent(ticketId)}/analyses`,
    { method: 'POST', csrfToken },
  )

export const getLatestAnalysis = (ticketId: string, signal?: AbortSignal) =>
  apiRequest<Analysis | null>(
    `/tickets/${encodeURIComponent(ticketId)}/analyses/latest`,
    { signal },
  )

export const getAnalysis = (analysisId: string, signal?: AbortSignal) =>
  apiRequest<Analysis>(`/analyses/${encodeURIComponent(analysisId)}`, {
    signal,
  })

export const retryAnalysis = (analysisId: string, csrfToken: string) =>
  apiRequest<AnalysisAccepted>(
    `/analyses/${encodeURIComponent(analysisId)}/retry`,
    { method: 'POST', csrfToken },
  )

export const overrideTicketPriority = (
  ticketId: string,
  input: PriorityOverrideInput,
  csrfToken: string,
) =>
  apiRequest<TicketDetail>(
    `/tickets/${encodeURIComponent(ticketId)}/priority-override`,
    { method: 'POST', body: input, csrfToken },
  )
