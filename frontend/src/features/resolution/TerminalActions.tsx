import { useState, type FormEvent } from 'react'

import type { SupportResponse, TicketDetail } from '../../api/types'
import { formatDate } from '../../components/TicketTable'
import { formValue } from './formValue'

interface Props {
  ticket: TicketDetail
  response: SupportResponse | null
  pending: boolean
  onResolve: (summary: string) => void
  onEscalate: (destination: string, reason: string) => void
}

export function TerminalActions({
  ticket,
  response,
  pending,
  onResolve,
  onEscalate,
}: Props) {
  const [error, setError] = useState<string | null>(null)
  const terminal = ticket.status === 'resolved' || ticket.status === 'escalated'
  if (terminal)
    return (
      <div className="terminal-state" role="status">
        <p className="section-label">Terminal state</p>
        <h3>Ticket {ticket.status}</h3>
        <p>
          {ticket.status === 'resolved'
            ? ticket.resolved_at
              ? formatDate(ticket.resolved_at)
              : 'Timestamp unavailable'
            : ticket.escalated_at
              ? formatDate(ticket.escalated_at)
              : 'Timestamp unavailable'}
        </p>
        {ticket.status === 'resolved' && (
          <p>
            {ticket.resolution_summary ?? 'No resolution summary provided.'}
          </p>
        )}
        {ticket.status === 'escalated' && (
          <dl className="resolution-details">
            <div>
              <dt>Destination</dt>
              <dd>{ticket.escalation_destination ?? 'Not provided'}</dd>
            </div>
            <div>
              <dt>Reason</dt>
              <dd>{ticket.escalation_reason ?? 'Not provided'}</dd>
            </div>
          </dl>
        )}
        <p className="muted">Terminal actions are disabled for this ticket.</p>
      </div>
    )

  const resolve = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const summary = formValue(
      new FormData(event.currentTarget),
      'resolution_summary',
    )
    if (summary.length < 10) {
      setError('Provide at least 10 characters summarizing the resolution.')
      return
    }
    setError(null)
    onResolve(summary)
  }
  const escalate = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const data = new FormData(event.currentTarget)
    const destination = formValue(data, 'escalation_destination')
    const reason = formValue(data, 'escalation_reason')
    if (destination.length < 3 || reason.length < 5) {
      setError(
        'Provide a destination of at least 3 characters and a reason of at least 5 characters.',
      )
      return
    }
    setError(null)
    onEscalate(destination, reason)
  }

  return (
    <div className="terminal-actions">
      {response?.status === 'approved' && (
        <form className="resolution-block" onSubmit={resolve}>
          <p className="section-label">Close workflow</p>
          <h3>Resolve ticket</h3>
          <div className="field">
            <label htmlFor="resolution-summary">Resolution summary</label>
            <textarea id="resolution-summary" name="resolution_summary" />
          </div>
          <button className="button button--primary" disabled={pending}>
            Resolve ticket
          </button>
        </form>
      )}
      <form className="resolution-block escalation-form" onSubmit={escalate}>
        <p className="section-label">Explicit escalation</p>
        <h3>Escalate ticket</h3>
        <p>
          This will move the ticket to a terminal escalated state. Confirm the
          destination and reason.
        </p>
        <div className="field">
          <label htmlFor="escalation-destination">Destination</label>
          <input id="escalation-destination" name="escalation_destination" />
        </div>
        <div className="field">
          <label htmlFor="escalation-reason">Reason</label>
          <textarea id="escalation-reason" name="escalation_reason" />
        </div>
        <button className="button button--outline" disabled={pending}>
          Escalate ticket with confirmation
        </button>
      </form>
      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
    </div>
  )
}
