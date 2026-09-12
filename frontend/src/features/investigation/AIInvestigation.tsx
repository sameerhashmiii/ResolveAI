import { useQuery } from '@tanstack/react-query'

import { getLatestAnalysis } from '../../api/analyses'
import type {
  Investigation,
  InvestigationStep,
  TicketDetail,
} from '../../api/types'
import { InvestigationObservation } from './InvestigationObservations'
import { useInvestigation } from './useInvestigation'

interface AIInvestigationProps {
  ticket: TicketDetail
  csrfToken: string | null
}

function isStep(value: unknown): value is InvestigationStep {
  if (typeof value !== 'object' || value === null) return false
  const step = value as Partial<InvestigationStep>
  return (
    typeof step.id === 'string' &&
    typeof step.label === 'string' &&
    typeof step.status === 'string' &&
    (typeof step.tool_name === 'string' || step.tool_name === null) &&
    typeof step.source_count === 'number' &&
    typeof step.duration_ms === 'number'
  )
}

function isInvestigation(value: unknown): value is Investigation {
  if (typeof value !== 'object' || value === null) return false
  const candidate = value as Partial<Investigation>
  return (
    typeof candidate.id === 'string' &&
    typeof candidate.status === 'string' &&
    typeof candidate.reference_time === 'string' &&
    Array.isArray(candidate.steps) &&
    candidate.steps.every(isStep)
  )
}

function formatReferenceTime(value: string) {
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString()
}

function CompletedInvestigation({
  investigation,
}: {
  investigation: Investigation
}) {
  return (
    <div className="investigation-results">
      <div className="investigation-reference">
        <div>
          <span>Reference time</span>
          <strong>{formatReferenceTime(investigation.reference_time)}</strong>
        </div>
        {investigation.reference_basis === 'curated_demo_scenario' && (
          <span className="badge badge--synthetic">
            Curated synthetic reference time
          </span>
        )}
      </div>

      <section
        className="investigation-timeline"
        aria-labelledby="investigation-timeline-title"
      >
        <h3 id="investigation-timeline-title">Investigation Timeline</h3>
        {investigation.steps.length === 0 ? (
          <p className="observation-unavailable">
            No persisted steps were returned.
          </p>
        ) : (
          <ol>
            {investigation.steps.map((step) => (
              <li key={step.id} className={`step--${step.status}`}>
                <span aria-hidden="true" />
                <div>
                  <strong>{step.label}</strong>
                  <p>
                    <span className="capitalize">
                      {step.status.replaceAll('_', ' ')}
                    </span>
                    {' · '}
                    {step.source_count} source
                    {step.source_count === 1 ? '' : 's'}
                    {` · ${String(step.duration_ms)} ms`}
                  </p>
                  {step.status !== 'completed' &&
                    step.status !== 'succeeded' && (
                      <small>
                        Limitation: this step did not complete successfully.
                      </small>
                    )}
                </div>
              </li>
            ))}
          </ol>
        )}
      </section>

      <div className="investigation-observations">
        {investigation.steps.map((step) => (
          <InvestigationObservation key={step.id} step={step} />
        ))}
      </div>
    </div>
  )
}

export function AIInvestigation({ ticket, csrfToken }: AIInvestigationProps) {
  const triage = useQuery({
    queryKey: ['ticket', ticket.id, 'analysis', 'latest'],
    queryFn: ({ signal }) => getLatestAnalysis(ticket.id, signal),
    enabled: Boolean(ticket.id),
  })
  const triageCompleted = triage.data?.status === 'completed'
  const {
    investigation: rawInvestigation,
    latest,
    start,
    retry,
  } = useInvestigation(ticket.id, csrfToken, triageCompleted)
  const investigation = isInvestigation(rawInvestigation)
    ? rawInvestigation
    : null
  const invalidResponse = rawInvestigation != null && !investigation
  const active =
    investigation?.status === 'queued' || investigation?.status === 'running'
  const failed =
    investigation?.status === 'failed' || investigation?.status === 'timed_out'
  const actionError = start.error ?? retry.error

  return (
    <section
      className="content-card investigation-card"
      aria-labelledby="ai-investigation-title"
    >
      <div className="section-heading investigation-heading">
        <div>
          <p className="section-label">Persisted tool observations</p>
          <h2 id="ai-investigation-title">AI Investigation</h2>
        </div>
        {investigation && (
          <span
            className={`badge badge--${investigation.status.replaceAll('_', '-')}`}
          >
            {investigation.status.replaceAll('_', ' ')}
          </span>
        )}
      </div>
      <p className="investigation-disclaimer">
        Collected observations only. Root-cause inference and recommendations
        are not generated in this phase.
      </p>

      {triage.isPending && (
        <div className="investigation-state" role="status">
          Checking structured triage status...
        </div>
      )}
      {!triage.isPending && !triageCompleted && (
        <div className="investigation-state">
          <h3>Structured triage required</h3>
          <p>
            Complete AI Ticket Triage before starting an investigation. No
            investigation action is available until triage completes.
          </p>
        </div>
      )}
      {triageCompleted && latest.isPending && !investigation && (
        <div className="investigation-state" role="status">
          Checking for an existing investigation...
        </div>
      )}
      {triageCompleted && latest.isError && !investigation && (
        <div
          className="investigation-state investigation-state--error"
          role="alert"
        >
          Investigation status could not be loaded. {latest.error.message}
        </div>
      )}
      {triageCompleted && invalidResponse && (
        <div
          className="investigation-state investigation-state--error"
          role="alert"
        >
          Investigation data is unavailable because the service returned an
          invalid response.
        </div>
      )}
      {triageCompleted &&
        !latest.isPending &&
        !latest.isError &&
        !investigation &&
        !invalidResponse && (
          <div className="investigation-state investigation-empty">
            <h3>Collect operational observations</h3>
            <p>
              Run the persisted investigation workflow to collect factual
              records from the configured tools.
            </p>
            <button
              className="button button--primary"
              type="button"
              onClick={() => start.mutate()}
              disabled={start.isPending}
            >
              {start.isPending
                ? 'Starting investigation...'
                : 'Start investigation'}
            </button>
          </div>
        )}
      {(active || (start.isSuccess && !investigation)) && (
        <div className="investigation-active" role="status" aria-live="polite">
          <span className="activity-indicator" aria-hidden="true" />
          <div>
            <h3>
              {investigation?.status === 'running'
                ? 'Investigation running'
                : 'Investigation queued'}
            </h3>
            <p>
              Tool status refreshes automatically while the workflow is active.
            </p>
          </div>
        </div>
      )}
      {investigation?.status === 'completed' && (
        <CompletedInvestigation investigation={investigation} />
      )}
      {investigation && failed && (
        <div
          className="investigation-state investigation-state--error"
          role="alert"
        >
          <p className="section-label">Observations unavailable</p>
          <h3>
            {investigation.status === 'timed_out'
              ? 'Investigation timed out'
              : 'Investigation failed safely'}
          </h3>
          <p>
            The workflow did not complete. Existing ticket and tool records were
            not changed.
          </p>
          <button
            className="button button--outline"
            type="button"
            onClick={() => retry.mutate(investigation.id)}
            disabled={retry.isPending}
          >
            {retry.isPending ? 'Retrying...' : 'Retry investigation'}
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
