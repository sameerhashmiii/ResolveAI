import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'

import { getDashboardOverview } from '../api/dashboard'
import { TicketTable } from '../components/TicketTable'

export function DashboardPage() {
  const overview = useQuery({
    queryKey: ['dashboard', 'overview'],
    queryFn: ({ signal }) => getDashboardOverview(signal),
  })

  return (
    <div className="page">
      <header className="page-header page-header--split">
        <div>
          <p className="eyebrow">Operations overview</p>
          <h1>Service desk, at a glance.</h1>
          <p>Current workload and recent movement across your support queue.</p>
        </div>
        <Link className="button button--primary" to="/tickets/new">
          Create ticket
        </Link>
      </header>

      {overview.isPending && (
        <div className="loading-panel" role="status">
          Loading overview...
        </div>
      )}
      {overview.isError && (
        <div className="error-panel" role="alert">
          <strong>Overview unavailable</strong>
          <p>{overview.error.message}</p>
          <button
            className="text-button"
            type="button"
            onClick={() => void overview.refetch()}
          >
            Try again
          </button>
        </div>
      )}
      {overview.data && (
        <>
          <section className="metrics" aria-label="Ticket metrics">
            {(
              [
                ['Total tickets', overview.data.total_tickets],
                ['Open', overview.data.open_tickets],
                ['Resolved', overview.data.resolved_tickets],
                ['Escalated', overview.data.escalated_tickets],
              ] satisfies Array<[string, number]>
            ).map(([label, value], index) => (
              <article key={label}>
                <span>0{index + 1}</span>
                <strong>{value}</strong>
                <p>{label}</p>
              </article>
            ))}
          </section>
          <section className="content-card">
            <div className="section-heading">
              <div>
                <p className="section-label">Latest activity</p>
                <h2>Recent tickets</h2>
              </div>
              <Link to="/tickets">View all tickets</Link>
            </div>
            {overview.data.recent_tickets.length > 0 ? (
              <TicketTable tickets={overview.data.recent_tickets} />
            ) : (
              <div className="empty-state">
                <span aria-hidden="true">01</span>
                <h3>Your queue is ready.</h3>
                <p>
                  No tickets have been submitted yet. Create the first request
                  to begin tracking work.
                </p>
                <Link className="button button--outline" to="/tickets/new">
                  Create first ticket
                </Link>
              </div>
            )}
          </section>
        </>
      )}
    </div>
  )
}
