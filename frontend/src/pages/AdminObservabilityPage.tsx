import { useQuery } from '@tanstack/react-query'

import { getAdminHealth } from '../api/adminHealth'
import { getAiPerformance, getAnalyticsOverview } from '../api/analytics'
import { ObservabilityState } from '../components/observability/ObservabilityState'
import { SafeAggregateList } from '../components/observability/SafeAggregateList'

function formatDate(value: string) {
  const date = new Date(value)
  return Number.isNaN(date.getTime())
    ? 'Not reported'
    : new Intl.DateTimeFormat(undefined, {
        dateStyle: 'medium',
        timeStyle: 'short',
      }).format(date)
}

function formatPercent(value: number) {
  return `${(value <= 1 ? value * 100 : value).toFixed(1)}%`
}

const SyntheticLabel = () => (
  <span className="synthetic-label">Synthetic demo measurement</span>
)

export function AdminObservabilityPage() {
  const overview = useQuery({
    queryKey: ['analytics', 'overview'],
    queryFn: ({ signal }) => getAnalyticsOverview(signal),
  })
  const performance = useQuery({
    queryKey: ['analytics', 'ai-performance'],
    queryFn: ({ signal }) => getAiPerformance(signal),
  })
  const health = useQuery({
    queryKey: ['admin', 'health'],
    queryFn: ({ signal }) => getAdminHealth(signal),
    refetchInterval: 30_000,
  })
  const refreshing =
    overview.isFetching || performance.isFetching || health.isFetching
  const refresh = () => {
    void overview.refetch()
    void performance.refetch()
    void health.refetch()
  }

  return (
    <div className="page observability-page">
      <header className="page-header page-header--split">
        <div>
          <p className="eyebrow">Administrator observability</p>
          <h1>Evidence, not theater.</h1>
          <p>
            A bounded view of demo operations, evaluation aggregates, and
            service health. These measurements are synthetic and are not
            production telemetry.
          </p>
        </div>
        <button
          className="button button--outline"
          type="button"
          disabled={refreshing}
          onClick={refresh}
        >
          {refreshing ? 'Refreshing...' : 'Refresh all'}
        </button>
      </header>

      <section
        className="observability-section"
        aria-labelledby="operations-heading"
      >
        <div className="observability-section-heading">
          <div>
            <p className="section-label">01 / Operations</p>
            <h2 id="operations-heading">Ticket and workflow measurements</h2>
          </div>
          <SyntheticLabel />
        </div>
        {overview.isPending && (
          <ObservabilityState title="Operations analytics" />
        )}
        {overview.isError && (
          <ObservabilityState
            title="Operations analytics"
            error={overview.error}
            onRetry={() => void overview.refetch()}
          />
        )}
        {overview.data && (
          <div className="observability-body">
            <dl className="observability-provenance">
              <div>
                <dt>Source</dt>
                <dd>{overview.data.source}</dd>
              </div>
              <div>
                <dt>Methodology</dt>
                <dd>{overview.data.methodology}</dd>
              </div>
              <div>
                <dt>Measured</dt>
                <dd>{formatDate(overview.data.measured_at)}</dd>
              </div>
              <div>
                <dt>Dataset version</dt>
                <dd>{overview.data.dataset_version}</dd>
              </div>
            </dl>
            <div
              className="observability-metrics"
              aria-label="Synthetic demo ticket measurements"
            >
              {[
                ['Total', overview.data.tickets.total_tickets],
                ['Open', overview.data.tickets.open_tickets],
                ['Resolved', overview.data.tickets.resolved_tickets],
                ['Escalated', overview.data.tickets.escalated_tickets],
                [
                  'Resolution rate',
                  formatPercent(overview.data.tickets.resolution_rate),
                ],
              ].map(([label, value]) => (
                <article key={label}>
                  <SyntheticLabel />
                  <strong>{value}</strong>
                  <p>{label}</p>
                  <small>
                    Denominator: {overview.data.tickets.sample_count} demo
                    tickets
                  </small>
                </article>
              ))}
            </div>
            <div className="workflow-table">
              <div className="observability-subheading">
                <h3>Workflow execution</h3>
                <p>
                  <SyntheticLabel /> Completion is operational completion, not
                  AI accuracy.
                </p>
              </div>
              <div className="table-wrap">
                <table>
                  <caption>
                    Workflow aggregates with demo run denominators and versions.
                  </caption>
                  <thead>
                    <tr>
                      <th>Workflow</th>
                      <th>Version</th>
                      <th>Completed</th>
                      <th>Failed</th>
                      <th>Completion rate</th>
                      <th>Median duration</th>
                    </tr>
                  </thead>
                  <tbody>
                    {overview.data.workflows.map((workflow) => (
                      <tr key={`${workflow.name}-${workflow.workflow_version}`}>
                        <th scope="row">
                          {workflow.name}
                          <small>n={workflow.total} demo runs</small>
                        </th>
                        <td>{workflow.workflow_version}</td>
                        <td>{workflow.completed}</td>
                        <td>{workflow.failed}</td>
                        <td>{formatPercent(workflow.completion_rate)}</td>
                        <td>
                          {workflow.median_duration_ms.toLocaleString()} ms
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {overview.data.workflows.length === 0 && (
                <p className="aggregate-empty">
                  No workflow measurements are available.
                </p>
              )}
            </div>
          </div>
        )}
      </section>

      <section
        className="observability-section"
        aria-labelledby="evaluation-heading"
      >
        <div className="observability-section-heading">
          <div>
            <p className="section-label">02 / Evaluation</p>
            <h2 id="evaluation-heading">AI performance evaluation</h2>
          </div>
          <SyntheticLabel />
        </div>
        {performance.isPending && <ObservabilityState title="AI performance" />}
        {performance.isError && (
          <ObservabilityState
            title="AI performance"
            error={performance.error}
            onRetry={() => void performance.refetch()}
          />
        )}
        {performance.data && (
          <div className="observability-body">
            <p className="measurement-note">
              <SyntheticLabel /> Source: {performance.data.source}. Methodology:{' '}
              {performance.data.methodology}.
            </p>
            {performance.data.latest_run === null ? (
              <div className="evaluation-empty">
                <span aria-hidden="true">No run</span>
                <h3>No completed evaluation yet.</h3>
                <p>
                  Accuracy and quality metrics will appear only after a
                  synthetic evaluation run completes. Workflow completion rates
                  above are not a substitute.
                </p>
              </div>
            ) : (
              <div className="evaluation-grid">
                <div>
                  <h3>Latest aggregate metrics</h3>
                  <p className="measurement-note">
                    <SyntheticLabel /> Denominator:{' '}
                    {performance.data.latest_run.sample_count} evaluation
                    samples.
                  </p>
                  <SafeAggregateList
                    value={performance.data.latest_run.metrics}
                  />
                </div>
                <div>
                  <h3>Evaluation record</h3>
                  <dl className="observability-provenance observability-provenance--stacked">
                    <div>
                      <dt>Completed</dt>
                      <dd>
                        {formatDate(performance.data.latest_run.completed_at)}
                      </dd>
                    </div>
                    <div>
                      <dt>Dataset</dt>
                      <dd>{performance.data.latest_run.dataset_version}</dd>
                    </div>
                    <div>
                      <dt>Dataset checksum</dt>
                      <dd>{performance.data.latest_run.dataset_checksum}</dd>
                    </div>
                    <div>
                      <dt>Runner / workflow</dt>
                      <dd>
                        {performance.data.latest_run.runner_version} /{' '}
                        {performance.data.latest_run.workflow_version}
                      </dd>
                    </div>
                    <div>
                      <dt>Provider / model</dt>
                      <dd>
                        {performance.data.latest_run.provider} /{' '}
                        {performance.data.latest_run.model ?? 'Not reported'}
                      </dd>
                    </div>
                  </dl>
                  <h3>Methodology aggregates</h3>
                  <SafeAggregateList
                    value={performance.data.latest_run.methodology}
                    mode="methodology"
                  />
                </div>
              </div>
            )}
          </div>
        )}
      </section>

      <section
        className="observability-section"
        aria-labelledby="health-heading"
      >
        <div className="observability-section-heading">
          <div>
            <p className="section-label">03 / Service</p>
            <h2 id="health-heading">Component health</h2>
          </div>
          {health.data && (
            <span
              className={`health-status health-status--${health.data.status}`}
            >
              {health.data.status}
            </span>
          )}
        </div>
        {health.isPending && <ObservabilityState title="Service health" />}
        {health.isError && (
          <ObservabilityState
            title="Service health"
            error={health.error}
            onRetry={() => void health.refetch()}
          />
        )}
        {health.data && (
          <div className="observability-body">
            {health.data.status === 'degraded' && (
              <div className="degraded-notice" role="alert">
                <strong>Service is degraded.</strong> One or more components
                require attention.
              </div>
            )}
            <dl className="observability-provenance">
              <div>
                <dt>Service</dt>
                <dd>{health.data.service}</dd>
              </div>
              <div>
                <dt>Version</dt>
                <dd>{health.data.version}</dd>
              </div>
              <div>
                <dt>Environment</dt>
                <dd>{health.data.environment}</dd>
              </div>
              <div>
                <dt>Checked</dt>
                <dd>{formatDate(health.data.checked_at)}</dd>
              </div>
            </dl>
            <div className="component-health-grid">
              {health.data.components.map((component) => (
                <article
                  key={component.name}
                  className={`component-health component-health--${component.status}`}
                >
                  <span className="component-health-dot" aria-hidden="true" />
                  <div>
                    <h3>{component.name}</h3>
                    <p>{component.status}</p>
                  </div>
                  <div className="component-latency">
                    <SyntheticLabel />
                    <strong>{component.latency_ms.toLocaleString()} ms</strong>
                    <small>Demo check latency</small>
                  </div>
                </article>
              ))}
            </div>
          </div>
        )}
      </section>
    </div>
  )
}
