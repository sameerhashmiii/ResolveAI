import type {
  Analysis,
  AnalysisEntityValue,
  AnalysisFactorValue,
  TicketDetail,
} from '../../api/types'
import { useTicketTriage } from './useTicketTriage'
import { PriorityOverrideForm } from './PriorityOverrideForm'

interface AITicketTriageProps {
  ticket: TicketDetail
  csrfToken: string | null
}

const entityLabels: Record<string, string> = {
  user: 'User',
  location: 'Location',
  application: 'Application',
  device: 'Device',
  issue_type: 'Issue type',
  affected_scope: 'Affected scope',
  urgency: 'Urgency',
}

const entityKeys = [
  'user',
  'location',
  'application',
  'device',
  'issue_type',
  'affected_scope',
  'urgency',
] as const

const errorMessages: Record<string, string> = {
  provider_unavailable: 'The analysis provider is temporarily unavailable.',
  analysis_timeout: 'The analysis exceeded its allowed processing time.',
  invalid_provider_response:
    'The provider returned an unusable structured response.',
  analysis_failed: 'The ticket could not be analyzed.',
  configuration_error: 'Analysis is not configured for this environment.',
}

const categoryLabels: Record<string, string> = {
  vpn: 'VPN / Remote Access',
  network: 'Network',
  wifi: 'Wi-Fi',
  email: 'Email',
  password: 'Password',
  account_access: 'Account Access',
  hardware: 'Hardware',
  software: 'Software',
  application: 'Application',
  security: 'Security',
  other: 'Other',
}

const humanize = (value: string) =>
  value.replaceAll('_', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase())

const showEntity = (value: AnalysisEntityValue) =>
  Array.isArray(value) ? value.join(', ') : value

const showFactor = (value: AnalysisFactorValue) => {
  if (typeof value === 'boolean') return value ? 'Yes' : 'No'
  if (Array.isArray(value)) return value.join(', ')
  return value === null ? 'Not provided' : String(value)
}

function CompletedAnalysis({ analysis }: { analysis: Analysis }) {
  const entities = analysis.entities
    ? entityKeys.flatMap((key) => {
        const value = analysis.entities?.[key]
        return value !== null && value !== undefined && value.length !== 0
          ? ([[key, value]] as const)
          : []
      })
    : []
  const factors = Array.isArray(analysis.priority_factors)
    ? analysis.priority_factors.map((value) => [value, null] as const)
    : Object.entries(analysis.priority_factors ?? {})
  const priority = analysis.validated_priority ?? analysis.recommended_priority
  const confidence =
    analysis.category_confidence === null
      ? null
      : Math.round(
          Math.min(
            100,
            Math.max(
              0,
              analysis.category_confidence <= 1
                ? analysis.category_confidence * 100
                : analysis.category_confidence,
            ),
          ),
        )

  return (
    <div className="triage-results">
      <div className="triage-summary">
        <article>
          <span>Category recommendation</span>
          <strong>
            {analysis.category
              ? (categoryLabels[analysis.category] ??
                humanize(analysis.category))
              : 'Not identified'}
          </strong>
          <small>
            {confidence === null
              ? 'Confidence not provided'
              : `${String(confidence)}% confidence`}
          </small>
        </article>
        <article>
          <span>AI Priority Recommendation</span>
          <strong className="priority-recommendation">
            {priority?.toUpperCase() ?? 'Not recommended'}
          </strong>
          <small>
            {analysis.validated_priority
              ? 'Validated recommendation'
              : 'Model recommendation'}
          </small>
        </article>
      </div>
      {analysis.requires_manual_review && (
        <div className="triage-warning" role="status">
          <strong>Manual review required.</strong> Verify this recommendation
          before changing ticket workflow.
        </div>
      )}
      <div className="triage-columns">
        <div>
          <h3>Extracted entities</h3>
          {entities.length ? (
            <dl className="entity-list">
              {entities.map(([key, value]) => (
                <div key={key}>
                  <dt>{entityLabels[key] ?? humanize(key)}</dt>
                  <dd>{showEntity(value)}</dd>
                </div>
              ))}
            </dl>
          ) : (
            <p className="muted">No entities were identified.</p>
          )}
        </div>
        <div>
          <h3>Priority decision factors</h3>
          {factors.length ? (
            <ul className="factor-list">
              {factors.map(([key, value]) => (
                <li key={key}>
                  <span>{humanize(key)}</span>
                  {value !== null && <strong>{showFactor(value)}</strong>}
                </li>
              ))}
            </ul>
          ) : (
            <p className="muted">No priority factors were provided.</p>
          )}
        </div>
      </div>
      <dl className="analysis-meta">
        <div>
          <dt>Analysis type</dt>
          <dd>
            {analysis.mode === 'local_demo'
              ? 'Deterministic demo provider'
              : 'Hosted structured model'}
          </dd>
        </div>
        <div>
          <dt>Provider</dt>
          <dd>
            {analysis.provider}
            {analysis.model ? ` / ${analysis.model}` : ''}
          </dd>
        </div>
        <div>
          <dt>Workflow</dt>
          <dd>{analysis.workflow_version}</dd>
        </div>
        <div>
          <dt>Elapsed</dt>
          <dd>
            {analysis.duration_ms === null
              ? 'Not recorded'
              : `${(analysis.duration_ms / 1000).toFixed(1)}s`}
          </dd>
        </div>
      </dl>
    </div>
  )
}

export function AITicketTriage({ ticket, csrfToken }: AITicketTriageProps) {
  const { analysis, latest, analyze, retry } = useTicketTriage(
    ticket.id,
    csrfToken,
  )
  const active = analysis?.status === 'queued' || analysis?.status === 'running'
  const failed =
    analysis?.status === 'failed' || analysis?.status === 'timed_out'
  const actionError = analyze.error ?? retry.error

  return (
    <section
      className="content-card triage-card"
      aria-labelledby="triage-title"
    >
      <div className="triage-heading">
        <div>
          <p className="section-label">Recommendation support</p>
          <h2 id="triage-title">AI Ticket Triage</h2>
        </div>
        {analysis && (
          <span className="analysis-mode">
            {analysis.mode === 'local_demo'
              ? 'Deterministic demo analysis'
              : 'AI recommendation'}
          </span>
        )}
      </div>

      {latest.isPending && !analysis && (
        <div className="triage-state" role="status">
          Checking for existing analysis...
        </div>
      )}
      {latest.isError && !analysis && (
        <div className="triage-state triage-state--error" role="alert">
          Analysis status could not be loaded. {latest.error.message}
        </div>
      )}
      {!latest.isPending && !latest.isError && !analysis && (
        <div className="triage-empty">
          <h3>Classify and prioritize this request</h3>
          <p>
            Analyze the ticket for a category recommendation, structured
            entities, and priority guidance. Output is advisory and should be
            reviewed by a person.
          </p>
          <button
            className="button button--primary"
            onClick={() => analyze.mutate()}
            disabled={analyze.isPending}
          >
            {analyze.isPending ? 'Requesting analysis...' : 'Analyze ticket'}
          </button>
        </div>
      )}
      {(active || (analyze.isSuccess && !analysis)) && (
        <div className="triage-active" role="status" aria-live="polite">
          <span className="activity-indicator" aria-hidden="true" />
          <div>
            <h3>
              {analysis?.status === 'running'
                ? 'Analysis running'
                : 'Analysis queued'}
            </h3>
            <p>
              ResolveAI is processing this ticket. This status refreshes
              automatically.
            </p>
          </div>
        </div>
      )}
      {analysis?.status === 'completed' && (
        <CompletedAnalysis analysis={analysis} />
      )}
      {analysis && failed && (
        <div className="triage-failed" role="alert">
          <p className="section-label">Analysis unavailable</p>
          <h3>
            {analysis.status === 'timed_out'
              ? 'Analysis timed out'
              : 'Analysis failed safely'}
          </h3>
          <p>
            {errorMessages[analysis.error_code ?? ''] ??
              'The analysis could not be completed. Ticket data and workflow were not changed.'}
          </p>
          <button
            className="button button--outline"
            onClick={() => retry.mutate(analysis.id)}
            disabled={retry.isPending}
          >
            {retry.isPending ? 'Retrying...' : 'Retry analysis'}
          </button>
        </div>
      )}
      {actionError && (
        <p className="form-error" role="alert">
          {actionError.message}
        </p>
      )}
      {(analysis?.status === 'completed' || ticket.priority) && (
        <PriorityOverrideForm ticket={ticket} csrfToken={csrfToken} />
      )}
    </section>
  )
}
