import { apiRequest } from './client'
import type {
  CreateTicketInput,
  PaginatedTickets,
  TicketDetail,
  TicketEvent,
  UpdateTicketInput,
} from './types'

export interface TicketFilters {
  page: number
  pageSize: number
  q?: string
  status?: string
  priority?: string
}

export function getTickets(filters: TicketFilters, signal?: AbortSignal) {
  const params = new URLSearchParams({
    page: String(filters.page),
    page_size: String(filters.pageSize),
  })
  if (filters.q) params.set('q', filters.q)
  if (filters.status) params.set('status', filters.status)
  if (filters.priority) params.set('priority', filters.priority)
  return apiRequest<PaginatedTickets>(`/tickets?${params.toString()}`, {
    signal,
  })
}

export const createTicket = (input: CreateTicketInput, csrfToken: string) =>
  apiRequest<TicketDetail>('/tickets', {
    method: 'POST',
    body: input,
    csrfToken,
  })

export const getTicket = (id: string, signal?: AbortSignal) =>
  apiRequest<TicketDetail>(`/tickets/${encodeURIComponent(id)}`, { signal })

export const getTicketEvents = (id: string, signal?: AbortSignal) =>
  apiRequest<TicketEvent[]>(`/tickets/${encodeURIComponent(id)}/events`, {
    signal,
  })

export const updateTicket = (
  id: string,
  updates: UpdateTicketInput,
  csrfToken: string,
) =>
  apiRequest<TicketDetail>(`/tickets/${encodeURIComponent(id)}`, {
    method: 'PATCH',
    body: updates,
    csrfToken,
  })

export const assignTicket = (
  id: string,
  assigneeId: string | null,
  csrfToken: string,
) =>
  apiRequest<TicketDetail>(`/tickets/${encodeURIComponent(id)}/assign`, {
    method: 'POST',
    body: { assigned_to_id: assigneeId },
    csrfToken,
  })

export const getAssignableUsers = (signal?: AbortSignal) =>
  apiRequest<import('./types').UserSummary[]>('/users', { signal })
