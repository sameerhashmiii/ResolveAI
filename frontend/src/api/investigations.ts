import { apiRequest } from './client'
import type {
  Investigation,
  InvestigationAccepted,
  SimilarTicket,
  SimilarTicketsResponse,
} from './types'

export async function getSimilarTickets(
  ticketId: string,
  signal?: AbortSignal,
): Promise<SimilarTicketsResponse> {
  const response = await apiRequest<SimilarTicketsResponse | SimilarTicket[]>(
    `/tickets/${encodeURIComponent(ticketId)}/similar?top_k=5`,
    { signal },
  )
  return Array.isArray(response) ? { items: response } : response
}

export const createInvestigation = (ticketId: string, csrfToken: string) =>
  apiRequest<InvestigationAccepted>(
    `/tickets/${encodeURIComponent(ticketId)}/investigations`,
    { method: 'POST', csrfToken },
  )

export const getLatestInvestigation = (
  ticketId: string,
  signal?: AbortSignal,
) =>
  apiRequest<Investigation | null>(
    `/tickets/${encodeURIComponent(ticketId)}/investigations/latest`,
    { signal },
  )

export const getInvestigation = (
  investigationId: string,
  signal?: AbortSignal,
) =>
  apiRequest<Investigation>(
    `/investigations/${encodeURIComponent(investigationId)}`,
    { signal },
  )

export const retryInvestigation = (
  investigationId: string,
  csrfToken: string,
) =>
  apiRequest<InvestigationAccepted>(
    `/investigations/${encodeURIComponent(investigationId)}/retry`,
    { method: 'POST', csrfToken },
  )
