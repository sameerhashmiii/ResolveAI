import { useQuery } from '@tanstack/react-query'

import { getHealthReady, type HealthReadyResponse } from '../api/health'

const HEALTH_QUERY_KEY = ['health', 'ready'] as const

function isReady(data: HealthReadyResponse) {
  return data.status.toLowerCase() === 'ready'
}

function formatCheckedAt(timestamp?: string) {
  if (!timestamp) return 'Just now'

  const date = new Date(timestamp)
  if (Number.isNaN(date.getTime())) return 'Just now'

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date)
}

export function HealthPage() {
  const health = useQuery({
    queryKey: HEALTH_QUERY_KEY,
    queryFn: ({ signal }) => getHealthReady(signal),
    refetchInterval: 30_000,
  })

  const ready = health.data ? isReady(health.data) : false
  const state = health.isPending
    ? 'loading'
    : health.isError
      ? 'degraded'
      : ready
        ? 'ready'
        : 'degraded'

  return (
    <div className="app-shell">
      <header className="site-header">
        <a
          className="brand"
          href="/"
          aria-label="ResolveAI platform health home"
        >
          <span className="brand-mark" aria-hidden="true">
            R
          </span>
          <span>
            <strong>ResolveAI</strong>
            <small>Platform Operations</small>
          </span>
        </a>
        <span className="environment">Foundation environment</span>
      </header>

      <main>
        <section className="intro" aria-labelledby="page-title">
          <p className="eyebrow">Phase 1 | Platform foundation</p>
          <h1 id="page-title">Operational readiness, clearly resolved.</h1>
          <p className="lede">
            This screen verifies the core connection between the ResolveAI web
            experience and its backend readiness service. It is the platform
            foundation, not a simulation of product features.
          </p>
        </section>

        <section
          className={`health-card health-card--${state}`}
          aria-live="polite"
        >
          <div className="health-card__heading">
            <div>
              <p className="section-label">System status</p>
              <h2>Readiness endpoint</h2>
            </div>
            <span className="status-pill" role="status">
              <span className="status-dot" aria-hidden="true" />
              {state === 'loading'
                ? 'Checking'
                : state === 'ready'
                  ? 'Ready'
                  : 'Degraded'}
            </span>
          </div>

          {state === 'loading' && (
            <div className="state-content" data-testid="loading-state">
              <div className="loading-line" aria-hidden="true" />
              <p>Contacting the ResolveAI readiness service...</p>
            </div>
          )}

          {state === 'ready' && health.data && (
            <div className="state-content">
              <p className="state-message">
                The platform foundation is accepting traffic.
              </p>
              <dl className="health-details">
                <div>
                  <dt>Service</dt>
                  <dd>{health.data.service ?? 'ResolveAI API'}</dd>
                </div>
                <div>
                  <dt>Last verified</dt>
                  <dd>{formatCheckedAt(health.data.timestamp)}</dd>
                </div>
                <div>
                  <dt>Contract</dt>
                  <dd>GET /api/v1/health/ready</dd>
                </div>
              </dl>
            </div>
          )}

          {state === 'degraded' && (
            <div className="state-content">
              <p className="state-message">
                Readiness could not be confirmed. The platform may be starting
                or temporarily unavailable.
              </p>
              <p className="error-detail">
                {health.error instanceof Error
                  ? health.error.message
                  : `The service reported "${health.data?.status ?? 'unknown'}".`}
              </p>
              <button
                className="retry-button"
                type="button"
                onClick={() => void health.refetch()}
                disabled={health.isFetching}
              >
                {health.isFetching ? 'Checking again...' : 'Check again'}
              </button>
            </div>
          )}
        </section>

        <aside className="foundation-note" aria-labelledby="foundation-title">
          <p className="section-label">What this establishes</p>
          <h2 id="foundation-title">A dependable first signal</h2>
          <p>
            The health contract gives operators and delivery teams one clear,
            observable indication that the application boundary is working.
          </p>
          <div className="principles" aria-label="Foundation principles">
            <span>Typed API boundary</span>
            <span>Observable state</span>
            <span>Accessible by default</span>
          </div>
        </aside>
      </main>

      <footer>
        <span>ResolveAI</span>
        <span>Platform health</span>
      </footer>
    </div>
  )
}
