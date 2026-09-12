import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'

import { getAnalyticsOverview, getEvaluationSummary } from '../api/analytics'
import { useAuth } from '../auth/AuthContext'
import { ObservabilityState } from '../components/observability/ObservabilityState'
import { SafeAggregateList } from '../components/observability/SafeAggregateList'

const percent = (value: number) =>
  `${(value <= 1 ? value * 100 : value).toFixed(1)}%`

export function AnalyticsPage() {
  const { user } = useAuth()
  const overview = useQuery({
    queryKey: ['analytics', 'overview'],
    queryFn: ({ signal }) => getAnalyticsOverview(signal),
  })
  const evaluation = useQuery({
    queryKey: ['analytics', 'evaluation-summary'],
    queryFn: ({ signal }) => getEvaluationSummary(signal),
  })

  return (
    <div className="page observability-page">
      <header className="page-header page-header--split">
        <div>
          <p className="eyebrow">Stored aggregate measurements</p>
          <h1>Evaluation, with receipts.</h1>
          <p>
            Synthetic aggregates only. Cases held out from product runtime and
            case-level records are not exposed.
          </p>
        </div>
        {user?.role === 'administrator' && (
          <Link className="button button--outline" to="/admin/observability">
            Full observability and health
          </Link>
        )}
      </header>

      <section
        className="observability-section"
        aria-labelledby="workflow-summary"
      >
        <div className="observability-section-heading">
          <div>
            <p className="section-label">01 / Operations</p>
            <h2 id="workflow-summary">Workflow summary</h2>
          </div>
          <span className="synthetic-label">Synthetic demo measurement</span>
        </div>
        {overview.isPending && (
          <ObservabilityState title="Workflow analytics" />
        )}
        {overview.isError && (
          <ObservabilityState
            title="Workflow analytics"
            error={overview.error}
            onRetry={() => void overview.refetch()}
          />
        )}
        {overview.data && (
          <div className="observability-body">
            <p className="measurement-note">
              Source: {overview.data.source}. Methodology:{' '}
              {overview.data.methodology}. Dataset:{' '}
              {overview.data.dataset_version}. Denominator:{' '}
              {overview.data.tickets.sample_count} synthetic tickets.
            </p>
            <p className="trust-warning">
              <strong>Workflow completion is not accuracy.</strong> Completion
              only records whether a workflow reached its terminal state.
            </p>
            {overview.data.workflows.length ? (
              <div className="analytics-workflows">
                {overview.data.workflows.map((workflow) => (
                  <article
                    key={`${workflow.name}-${workflow.workflow_version}`}
                  >
                    <span>{workflow.name}</span>
                    <strong>{percent(workflow.completion_rate)}</strong>
                    <small>
                      n={workflow.total} runs / {workflow.workflow_version}
                    </small>
                  </article>
                ))}
              </div>
            ) : (
              <div className="evaluation-empty">
                <h3>No workflow aggregates yet.</h3>
                <p>
                  Measurements appear after stored synthetic workflows complete.
                </p>
              </div>
            )}
          </div>
        )}
      </section>

      <section
        className="observability-section"
        aria-labelledby="evaluation-summary"
      >
        <div className="observability-section-heading">
          <div>
            <p className="section-label">02 / Evaluation</p>
            <h2 id="evaluation-summary">Synthetic evaluation summary</h2>
          </div>
          <span className="synthetic-label">Aggregate only</span>
        </div>
        {evaluation.isPending && (
          <ObservabilityState title="Evaluation summary" />
        )}
        {evaluation.isError && (
          <ObservabilityState
            title="Evaluation summary"
            error={evaluation.error}
            onRetry={() => void evaluation.refetch()}
          />
        )}
        {evaluation.data && (
          <div className="observability-body">
            <p className="measurement-note">
              Source: {evaluation.data.source}. Methodology:{' '}
              {evaluation.data.methodology}.
            </p>
            {evaluation.data.latest_run ? (
              <div className="evaluation-grid">
                <div>
                  <h3>Stored metrics</h3>
                  <p className="measurement-note">
                    Denominator: {evaluation.data.latest_run.sample_count}{' '}
                    synthetic samples.
                  </p>
                  <SafeAggregateList
                    value={evaluation.data.latest_run.metrics}
                  />
                </div>
                <div>
                  <h3>Provenance</h3>
                  <dl className="observability-provenance observability-provenance--stacked">
                    <div>
                      <dt>Dataset / checksum</dt>
                      <dd>
                        {evaluation.data.latest_run.dataset_version} /{' '}
                        {evaluation.data.latest_run.dataset_checksum}
                      </dd>
                    </div>
                    <div>
                      <dt>Runner / workflow</dt>
                      <dd>
                        {evaluation.data.latest_run.runner_version} /{' '}
                        {evaluation.data.latest_run.workflow_version}
                      </dd>
                    </div>
                    <div>
                      <dt>Provider / model</dt>
                      <dd>
                        {evaluation.data.latest_run.provider} /{' '}
                        {evaluation.data.latest_run.model ?? 'Not reported'}
                      </dd>
                    </div>
                  </dl>
                  <h3>Methodology</h3>
                  <SafeAggregateList
                    value={evaluation.data.latest_run.methodology}
                    mode="methodology"
                  />
                </div>
              </div>
            ) : (
              <div className="evaluation-empty">
                <h3>No completed evaluation yet.</h3>
                <p>
                  No accuracy or quality claim is made until a stored synthetic
                  evaluation run exists.
                </p>
              </div>
            )}
          </div>
        )}
      </section>
    </div>
  )
}
