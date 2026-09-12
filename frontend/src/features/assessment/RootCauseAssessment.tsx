import { useQuery } from '@tanstack/react-query'

import { getLatestInvestigation } from '../../api/investigations'
import type { TicketDetail } from '../../api/types'
import { CompletedAssessment } from './CompletedAssessment'
import { parseAssessment } from './parsing'
import { useAssessment } from './useAssessment'

interface RootCauseAssessmentProps {
  ticket: TicketDetail
  csrfToken: string | null
}

export function RootCauseAssessment({
  ticket,
  csrfToken,
}: RootCauseAssessmentProps) {
  const investigationQuery = useQuery({
    queryKey: ['ticket', ticket.id, 'investigation', 'latest'],
    queryFn: ({ signal }) => getLatestInvestigation(ticket.id, signal),
    enabled: Boolean(ticket.id),
  })
  const prerequisiteMet = investigationQuery.data?.status === 'completed'
  const {
    assessment: rawAssessment,
    latest,
    start,
    retry,
  } = useAssessment(ticket.id, csrfToken, prerequisiteMet)
  const assessment = parseAssessment(rawAssessment)
  const invalidResponse = rawAssessment != null && !assessment
  const active =
    assessment?.status === 'queued' || assessment?.status === 'running'
  const failed =
    assessment?.status === 'failed' ||
    assessment?.status === 'timed_out' ||
    assessment?.status === 'timedout'
  const actionError = start.error ?? retry.error

  return (
    <section
      className="content-card assessment-card"
      aria-labelledby="assessment-title"
    >
      <div className="section-heading assessment-heading">
        <div>
          <p className="section-label">Grounded inference and guidance</p>
          <h2 id="assessment-title">Root Cause Assessment</h2>
        </div>
        {assessment && (
          <span
            className={`badge badge--${assessment.status.replaceAll('_', '-')}`}
          >
            {assessment.status.replaceAll('_', ' ')}
          </span>
        )}
      </div>
      {investigationQuery.isPending && (
        <div className="assessment-state" role="status">
          Checking investigation status...
        </div>
      )}
      {investigationQuery.isError && (
        <div className="assessment-state assessment-state--error" role="alert">
          Investigation prerequisite status could not be loaded.{' '}
          {investigationQuery.error.message}
        </div>
      )}
      {!investigationQuery.isPending &&
        !investigationQuery.isError &&
        !prerequisiteMet && (
          <div className="assessment-state">
            <h3>Completed investigation required</h3>
            <p>
              Complete evidence investigation first. An assessment can only use
              persisted observations from a completed investigation.
            </p>
          </div>
        )}
      {prerequisiteMet && latest.isPending && !assessment && (
        <div className="assessment-state" role="status">
          Checking for an existing assessment...
        </div>
      )}
      {prerequisiteMet && latest.isError && !assessment && (
        <div className="assessment-state assessment-state--error" role="alert">
          Assessment status could not be loaded. {latest.error.message}
        </div>
      )}
      {prerequisiteMet && invalidResponse && (
        <div className="assessment-state assessment-state--error" role="alert">
          Assessment data is unavailable because the service returned an invalid
          response.
        </div>
      )}
      {prerequisiteMet &&
        !latest.isPending &&
        !latest.isError &&
        !assessment &&
        !invalidResponse && (
          <div className="assessment-state assessment-empty">
            <h3>Assess the collected evidence</h3>
            <p>
              Generate a separate, reviewable inference and recommendation from
              the completed investigation.
            </p>
            <button
              className="button button--primary"
              type="button"
              onClick={() => start.mutate()}
              disabled={start.isPending}
            >
              {start.isPending
                ? 'Generating assessment...'
                : 'Generate assessment'}
            </button>
          </div>
        )}
      {(active || (start.isSuccess && !rawAssessment)) && (
        <div className="assessment-active" role="status" aria-live="polite">
          <span className="activity-indicator" aria-hidden="true" />
          <div>
            <h3>
              {assessment?.status === 'running'
                ? 'Assessment running'
                : 'Assessment queued'}
            </h3>
            <p>Status refreshes automatically while inference is active.</p>
          </div>
        </div>
      )}
      {assessment?.status === 'completed' && (
        <CompletedAssessment assessment={assessment} />
      )}
      {assessment && failed && (
        <div className="assessment-state assessment-state--error" role="alert">
          <h3>
            {assessment.status === 'failed'
              ? 'Assessment failed safely'
              : 'Assessment timed out'}
          </h3>
          <p>No recommendation was applied and no ticket action was taken.</p>
          <button
            className="button button--outline"
            type="button"
            onClick={() => retry.mutate(assessment.id)}
            disabled={retry.isPending}
          >
            {retry.isPending ? 'Retrying...' : 'Retry assessment'}
          </button>
        </div>
      )}
      {actionError && (
        <p className="form-error" role="alert">
          {actionError.message}
        </p>
      )}
    </section>
  )
}
