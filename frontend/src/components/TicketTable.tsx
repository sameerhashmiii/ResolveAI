import { Link } from 'react-router-dom'

import type { TicketSummary } from '../api/types'

export const formatDate = (value: string) => {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return 'Unknown'
  return new Intl.DateTimeFormat(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  }).format(date)
}

export const displayValue = (value?: string | null) =>
  value ? value.replaceAll('_', ' ') : 'Not specified'

export function StatusBadge({ value }: { value: string }) {
  return (
    <span
      className={`badge badge--${value.toLowerCase().replaceAll('_', '-')}`}
    >
      {displayValue(value)}
    </span>
  )
}

export function TicketTable({ tickets }: { tickets: TicketSummary[] }) {
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th scope="col">Ticket</th>
            <th scope="col">Requester</th>
            <th scope="col">Priority</th>
            <th scope="col">Status</th>
            <th scope="col">Updated</th>
          </tr>
        </thead>
        <tbody>
          {tickets.map((ticket) => (
            <tr key={ticket.id}>
              <td>
                <Link className="ticket-link" to={`/tickets/${ticket.id}`}>
                  <small>{ticket.ticket_number}</small>
                  <strong>{ticket.title}</strong>
                </Link>
              </td>
              <td>{ticket.requester_name}</td>
              <td className="capitalize">{displayValue(ticket.priority)}</td>
              <td>
                <StatusBadge value={ticket.status} />
              </td>
              <td>{formatDate(ticket.updated_at)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
