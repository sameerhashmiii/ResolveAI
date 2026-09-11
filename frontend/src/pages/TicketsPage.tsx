import { useQuery } from '@tanstack/react-query'
import { useEffect, useState, type FormEvent } from 'react'
import { Link, useSearchParams } from 'react-router-dom'

import { getTickets } from '../api/tickets'
import { TicketTable } from '../components/TicketTable'

const PAGE_SIZE = 15

export function TicketsPage() {
  const [params, setParams] = useSearchParams()
  const [search, setSearch] = useState(params.get('q') ?? '')
  const page = Math.max(1, Number(params.get('page')) || 1)
  const status = params.get('status') ?? ''
  const priority = params.get('priority') ?? ''
  const q = params.get('q') ?? ''

  useEffect(() => {
    setSearch(q)
  }, [q])

  const tickets = useQuery({
    queryKey: ['tickets', { page, q, status, priority }],
    queryFn: ({ signal }) =>
      getTickets({ page, pageSize: PAGE_SIZE, q, status, priority }, signal),
  })

  const update = (name: string, value: string) => {
    setParams((current) => {
      const next = new URLSearchParams(current)
      if (value) next.set(name, value)
      else next.delete(name)
      if (name !== 'page') next.delete('page')
      return next
    })
  }

  const submitSearch = (event: FormEvent) => {
    event.preventDefault()
    update('q', search.trim())
  }

  return (
    <div className="page">
      <header className="page-header page-header--split">
        <div>
          <p className="eyebrow">Ticket register</p>
          <h1>Every request, accounted for.</h1>
          <p>Search, filter, and follow work through resolution.</p>
        </div>
        <Link className="button button--primary" to="/tickets/new">
          Create ticket
        </Link>
      </header>
      <section className="content-card">
        <form className="filters" onSubmit={submitSearch} role="search">
          <label className="search-field" htmlFor="ticket-search">
            <span>Search tickets</span>
            <input
              id="ticket-search"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Number, title, or requester"
            />
          </label>
          <button className="button button--outline" type="submit">
            Search
          </button>
          <label htmlFor="status-filter">
            <span>Status</span>
            <select
              id="status-filter"
              value={status}
              onChange={(event) => update('status', event.target.value)}
            >
              <option value="">All statuses</option>
              <option value="new">New</option>
              <option value="in_progress">In progress</option>
              <option value="resolved">Resolved</option>
              <option value="escalated">Escalated</option>
            </select>
          </label>
          <label htmlFor="priority-filter">
            <span>Priority</span>
            <select
              id="priority-filter"
              value={priority}
              onChange={(event) => update('priority', event.target.value)}
            >
              <option value="">All priorities</option>
              <option value="p1">P1 Critical</option>
              <option value="p2">P2 High</option>
              <option value="p3">P3 Medium</option>
              <option value="p4">P4 Low</option>
            </select>
          </label>
        </form>
        {tickets.isPending && (
          <div className="loading-panel" role="status">
            Loading tickets...
          </div>
        )}
        {tickets.isError && (
          <div className="error-panel" role="alert">
            <strong>Tickets unavailable</strong>
            <p>{tickets.error.message}</p>
          </div>
        )}
        {tickets.data && tickets.data.items.length > 0 && (
          <TicketTable tickets={tickets.data.items} />
        )}
        {tickets.data && tickets.data.items.length === 0 && (
          <div className="empty-state">
            <span aria-hidden="true">00</span>
            <h3>No matching tickets.</h3>
            <p>
              {q || status || priority
                ? 'Adjust your search or filters to widen the results.'
                : 'Create the first request to begin tracking service work.'}
            </p>
          </div>
        )}
        {tickets.data && tickets.data.total > 0 && (
          <nav className="pagination" aria-label="Ticket pages">
            <p>
              Page {tickets.data.page} · {tickets.data.total} tickets
            </p>
            <div>
              <button
                className="button button--outline"
                type="button"
                disabled={page <= 1}
                onClick={() => update('page', String(page - 1))}
              >
                Previous
              </button>
              <button
                className="button button--outline"
                type="button"
                disabled={!tickets.data.has_next}
                onClick={() => update('page', String(page + 1))}
              >
                Next
              </button>
            </div>
          </nav>
        )}
      </section>
    </div>
  )
}
