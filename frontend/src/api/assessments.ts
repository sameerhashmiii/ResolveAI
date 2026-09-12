import { apiRequest } from './client'
import type { AssessmentAccepted } from './types'

export const createAssessment = (ticketId: string, csrfToken: string) =>
  apiRequest<AssessmentAccepted>(
    `/tickets/${encodeURIComponent(ticketId)}/assessments`,
    { method: 'POST', csrfToken },
  )

export const getLatestAssessment = (ticketId: string, signal?: AbortSignal) =>
  apiRequest<unknown>(
    `/tickets/${encodeURIComponent(ticketId)}/assessments/latest`,
    { signal },
  )

export const getAssessment = (assessmentId: string, signal?: AbortSignal) =>
  apiRequest<unknown>(`/assessments/${encodeURIComponent(assessmentId)}`, {
    signal,
  })

export const retryAssessment = (assessmentId: string, csrfToken: string) =>
  apiRequest<AssessmentAccepted>(
    `/assessments/${encodeURIComponent(assessmentId)}/retry`,
    { method: 'POST', csrfToken },
  )

export const getAssessmentExplanation = (
  assessmentId: string,
  signal?: AbortSignal,
) =>
  apiRequest<unknown>(
    `/assessments/${encodeURIComponent(assessmentId)}/explanation`,
    { signal },
  )
