import { ApiError, apiRequest } from './client'
import type {
  Recommendation,
  RecommendationStatus,
  SupportResponse,
  SupportResponseStatus,
  TicketDetail,
} from './types'

const recommendationStatuses: RecommendationStatus[] = [
  'proposed',
  'approved',
  'modified',
  'rejected',
  'completed',
]
const responseStatuses: SupportResponseStatus[] = [
  'draft',
  'approved',
  'rejected',
]
const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null

export function parseRecommendation(value: unknown): Recommendation | null {
  if (value === null) return null
  if (
    !isRecord(value) ||
    typeof value.id !== 'string' ||
    typeof value.ticket_id !== 'string' ||
    typeof value.assessment_id !== 'string' ||
    typeof value.title !== 'string' ||
    typeof value.original_instructions !== 'string' ||
    typeof value.instructions !== 'string' ||
    typeof value.action_type !== 'string' ||
    typeof value.requires_approval !== 'boolean' ||
    !recommendationStatuses.includes(value.status as RecommendationStatus) ||
    (typeof value.decided_by_id !== 'string' && value.decided_by_id !== null) ||
    (typeof value.decision_reason !== 'string' &&
      value.decision_reason !== null) ||
    (typeof value.decided_at !== 'string' && value.decided_at !== null) ||
    typeof value.created_at !== 'string' ||
    typeof value.updated_at !== 'string'
  )
    throw new ApiError('ResolveAI returned an invalid recommendation response.')
  return value as unknown as Recommendation
}

export function parseSupportResponse(value: unknown): SupportResponse | null {
  if (value === null) return null
  if (
    !isRecord(value) ||
    typeof value.id !== 'string' ||
    typeof value.ticket_id !== 'string' ||
    typeof value.assessment_id !== 'string' ||
    typeof value.recommendation_id !== 'string' ||
    typeof value.generated_by !== 'string' ||
    typeof value.provider !== 'string' ||
    (typeof value.model !== 'string' && value.model !== null) ||
    typeof value.mode !== 'string' ||
    typeof value.draft_body !== 'string' ||
    (typeof value.final_body !== 'string' && value.final_body !== null) ||
    !responseStatuses.includes(value.status as SupportResponseStatus) ||
    typeof value.created_by_id !== 'string' ||
    (typeof value.approved_by_id !== 'string' &&
      value.approved_by_id !== null) ||
    (typeof value.rejected_by_id !== 'string' &&
      value.rejected_by_id !== null) ||
    (typeof value.rejection_reason !== 'string' &&
      value.rejection_reason !== null) ||
    (typeof value.approved_at !== 'string' && value.approved_at !== null) ||
    (typeof value.rejected_at !== 'string' && value.rejected_at !== null) ||
    typeof value.created_at !== 'string' ||
    typeof value.updated_at !== 'string' ||
    value.approval_semantics !== 'approval_only_not_sent'
  )
    throw new ApiError('ResolveAI returned an invalid customer response.')
  return value as unknown as SupportResponse
}

async function guarded<T>(
  request: Promise<unknown>,
  parse: (value: unknown) => T,
) {
  return parse(await request)
}

export const getLatestRecommendation = (
  ticketId: string,
  signal?: AbortSignal,
) =>
  guarded(
    apiRequest<unknown>(
      `/tickets/${encodeURIComponent(ticketId)}/recommendations/latest`,
      { signal },
    ),
    parseRecommendation,
  )

export const decideRecommendation = (
  recommendationId: string,
  input: {
    decision: 'approve' | 'reject' | 'modify'
    reason: string
    modified_instructions?: string
  },
  csrfToken: string,
) =>
  guarded(
    apiRequest<unknown>(
      `/recommendations/${encodeURIComponent(recommendationId)}/decision`,
      { method: 'POST', body: input, csrfToken },
    ),
    (value) => {
      const parsed = parseRecommendation(value)
      if (!parsed) throw new ApiError('ResolveAI returned no recommendation.')
      return parsed
    },
  )

export const getLatestResponse = (ticketId: string, signal?: AbortSignal) =>
  guarded(
    apiRequest<unknown>(
      `/tickets/${encodeURIComponent(ticketId)}/responses/latest`,
      { signal },
    ),
    parseSupportResponse,
  )

const responseMutation = (
  path: string,
  options: Parameters<typeof apiRequest>[1],
) =>
  guarded(apiRequest<unknown>(path, options), (value) => {
    const parsed = parseSupportResponse(value)
    if (!parsed) throw new ApiError('ResolveAI returned no customer response.')
    return parsed
  })

export const generateResponse = (ticketId: string, csrfToken: string) =>
  responseMutation(`/tickets/${encodeURIComponent(ticketId)}/responses`, {
    method: 'POST',
    csrfToken,
  })

export const saveResponse = (
  responseId: string,
  draftBody: string,
  csrfToken: string,
) =>
  responseMutation(`/responses/${encodeURIComponent(responseId)}`, {
    method: 'PATCH',
    body: { draft_body: draftBody },
    csrfToken,
  })

export const approveResponse = (responseId: string, csrfToken: string) =>
  responseMutation(`/responses/${encodeURIComponent(responseId)}/approve`, {
    method: 'POST',
    csrfToken,
  })

export const rejectResponse = (
  responseId: string,
  reason: string,
  csrfToken: string,
) =>
  responseMutation(`/responses/${encodeURIComponent(responseId)}/reject`, {
    method: 'POST',
    body: { reason },
    csrfToken,
  })

export const resolveTicket = (
  ticketId: string,
  responseId: string,
  resolutionSummary: string,
  csrfToken: string,
) =>
  apiRequest<TicketDetail>(`/tickets/${encodeURIComponent(ticketId)}/resolve`, {
    method: 'POST',
    body: { response_id: responseId, resolution_summary: resolutionSummary },
    csrfToken,
  })

export const escalateTicket = (
  ticketId: string,
  destination: string,
  reason: string,
  csrfToken: string,
) =>
  apiRequest<TicketDetail>(
    `/tickets/${encodeURIComponent(ticketId)}/escalate`,
    {
      method: 'POST',
      body: { destination, reason },
      csrfToken,
    },
  )
