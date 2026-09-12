import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'
import { Link, useParams } from 'react-router-dom'

import {
  assignTicket,
  getAssignableUsers,
  getTicket,
  getTicketEvents,
  updateTicket,
} from '../api/tickets'
import { useAuth } from '../auth/AuthContext'
import {
  displayValue,
  formatDate,
  StatusBadge,
} from '../components/TicketTable'
import { KnowledgeSources } from '../features/knowledge/KnowledgeSources'
import { AITicketTriage } from '../features/triage/AITicketTriage'

export function TicketDetailPage() {
  const { id = '' } = useParams()
  const { csrfToken, user } = useAuth()
  const queryClient = useQueryClient()
  const [actionError, setActionError] = useState<string | null>(null)
  const ticket = useQuery({
    queryKey: ['ticket', id],
    queryFn: ({ signal }) => getTicket(id, signal),
    enabled: Boolean(id),
  })
  const events = useQuery({
    queryKey: ['ticket', id, 'events'],
    queryFn: ({ signal }) => getTicketEvents(id, signal),
    enabled: Boolean(id),
  })
  const users = useQuery({
    queryKey: ['assignable-users'],
    queryFn: ({ signal }) => getAssignableUsers(signal),
  })

  const refreshTicket = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['ticket', id] }),
      queryClient.invalidateQueries({ queryKey: ['tickets'] }),
      queryClient.invalidateQueries({ queryKey: ['dashboard'] }),
    ])
  }
  const statusMutation = useMutation({
    mutationFn: (status: 'new' | 'in_progress' | 'resolved' | 'escalated') => {
      if (!csrfToken)
        throw new Error('Your session is missing a security token.')
      return updateTicket(id, { status }, csrfToken)
    },
    onSuccess: refreshTicket,
    onError: (error) => setActionError(error.message),
  })
  const assignmentMutation = useMutation({
    mutationFn: (assigneeId: string | null) => {
      if (!csrfToken)
        throw new Error('Your session is missing a security token.')
      return assignTicket(id, assigneeId, csrfToken)
    },
    onSuccess: refreshTicket,
    onError: (error) => setActionError(error.message),
  })

  if (ticket.isPending)
    return (
      <div className="page">
        <div className="loading-panel" role="status">
          Loading ticket...
        </div>
      </div>
    )
  if (ticket.isError)
    return (
      <div className="page">
        <div className="error-panel" role="alert">
          <strong>Ticket unavailable</strong>
          <p>{ticket.error.message}</p>
          <Link to="/tickets">Return to tickets</Link>
        </div>
      </div>
    )

  const item = ticket.data
  const submitWorkflow = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setActionError(null)
    const data = new FormData(event.currentTarget)
    const statusValue = data.get('status')
    const assigneeValue = data.get('assigned_to_id')
    const nextStatus = (
      typeof statusValue === 'string' ? statusValue : 'new'
    ) as 'new' | 'in_progress' | 'resolved' | 'escalated'
    const nextAssignee = typeof assigneeValue === 'string' ? assigneeValue : ''
    if (nextStatus !== item.status) statusMutation.mutate(nextStatus)
    if (nextAssignee !== (item.assigned_to?.id ?? ''))
      assignmentMutation.mutate(nextAssignee || null)
  }
  const details: Array<[string, string | null | undefined]> = [
    ['Requester', item.requester_name],
    ['Department', item.requester_department],
    ['Location', item.location],
    ['Device', item.device],
    ['Application', item.application],
    ['Category', item.category],
  ]

  return (
    <div className="page">
      <Link className="back-link" to="/tickets">
        ← Back to tickets
      </Link>
      <header className="detail-header">
        <div>
          <p className="eyebrow">{item.ticket_number}</p>
          <h1>{item.title}</h1>
          <p>
            Opened {formatDate(item.created_at)} by{' '}
            {item.created_by.display_name}
          </p>
        </div>
        <StatusBadge value={item.status} />
      </header>
      <div className="detail-grid">
        <div className="detail-primary">
          <section className="content-card prose-card">
            <p className="section-label">Request description</p>
            <h2>Reported issue</h2>
            <p>{item.description}</p>
          </section>
          <AITicketTriage ticket={item} csrfToken={csrfToken} />
          <KnowledgeSources ticket={item} isAuthenticated={Boolean(user)} />
          <section className="content-card">
            <div className="section-heading">
              <div>
                <p className="section-label">Audit trail</p>
                <h2>Activity</h2>
              </div>
            </div>
            {events.isPending && (
              <div className="loading-panel" role="status">
                Loading activity...
              </div>
            )}
            {events.isError && (
              <p className="muted">Activity could not be loaded.</p>
            )}
            {events.data && events.data.length === 0 && (
              <div className="empty-state empty-state--compact">
                <h3>No activity yet.</h3>
                <p>Updates to this ticket will appear here.</p>
              </div>
            )}
            {events.data && events.data.length > 0 && (
              <ol className="timeline">
                {events.data.map((event) => (
                  <li key={event.id}>
                    <span aria-hidden="true" />
                    <div>
                      <strong>{event.summary}</strong>
                      <p>
                        {event.actor?.display_name ?? 'System'} ·{' '}
                        {formatDate(event.created_at)}
                      </p>
                    </div>
                  </li>
                ))}
              </ol>
            )}
          </section>
        </div>
        <aside className="detail-aside">
          <form
            className="content-card context-card workflow-card"
            onSubmit={submitWorkflow}
          >
            <p className="section-label">Workflow</p>
            <div className="field">
              <label htmlFor="ticket-status">Status</label>
              <select
                id="ticket-status"
                name="status"
                defaultValue={item.status}
              >
                <option value="new">New</option>
                <option value="in_progress">In progress</option>
                <option value="resolved">Resolved</option>
                <option value="escalated">Escalated</option>
              </select>
            </div>
            <div className="field">
              <label htmlFor="ticket-assignee">Assigned to</label>
              <select
                id="ticket-assignee"
                name="assigned_to_id"
                defaultValue={item.assigned_to?.id ?? ''}
                disabled={users.isPending || users.isError}
              >
                <option value="">Unassigned</option>
                {users.data?.map((user) => (
                  <option key={user.id} value={user.id}>
                    {user.display_name}
                  </option>
                ))}
              </select>
            </div>
            {actionError && (
              <p className="form-error" role="alert">
                {actionError}
              </p>
            )}
            <button
              className="button button--primary"
              disabled={
                statusMutation.isPending || assignmentMutation.isPending
              }
            >
              {statusMutation.isPending || assignmentMutation.isPending
                ? 'Saving...'
                : 'Save workflow'}
            </button>
          </form>
          <section className="content-card context-card">
            <p className="section-label">Ownership</p>
            <dl>
              <div>
                <dt>Assigned to</dt>
                <dd>{item.assigned_to?.display_name ?? 'Unassigned'}</dd>
              </div>
              <div>
                <dt>Priority</dt>
                <dd className="ownership-priority capitalize">
                  {displayValue(item.priority)}
                  {item.priority_overridden && (
                    <span className="badge badge--human">Human override</span>
                  )}
                </dd>
              </div>
              {item.priority_overridden && item.priority_override_reason && (
                <div>
                  <dt>Override reason</dt>
                  <dd>{item.priority_override_reason}</dd>
                </div>
              )}
              <div>
                <dt>Status</dt>
                <dd className="capitalize">{displayValue(item.status)}</dd>
              </div>
              <div>
                <dt>Last updated</dt>
                <dd>{formatDate(item.updated_at)}</dd>
              </div>
            </dl>
          </section>
          <section className="content-card context-card">
            <p className="section-label">Request context</p>
            <dl>
              {details.map(([label, value]) => (
                <div key={label}>
                  <dt>{label}</dt>
                  <dd className="capitalize">{displayValue(value)}</dd>
                </div>
              ))}
            </dl>
          </section>
        </aside>
      </div>
    </div>
  )
}
