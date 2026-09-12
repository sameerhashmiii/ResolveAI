import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'

import { overrideTicketPriority } from '../../api/analyses'
import type { TicketDetail, TicketPriority } from '../../api/types'

interface PriorityOverrideFormProps {
  ticket: TicketDetail
  csrfToken: string | null
}

export function PriorityOverrideForm({
  ticket,
  csrfToken,
}: PriorityOverrideFormProps) {
  const queryClient = useQueryClient()
  const [validationError, setValidationError] = useState<string | null>(null)
  const mutation = useMutation({
    mutationFn: (input: { priority: TicketPriority; reason: string }) => {
      if (!csrfToken)
        throw new Error('Your session is missing a security token.')
      return overrideTicketPriority(ticket.id, input, csrfToken)
    },
    onSuccess: async (updatedTicket) => {
      queryClient.setQueryData(['ticket', ticket.id], updatedTicket)
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['ticket', ticket.id] }),
        queryClient.invalidateQueries({
          queryKey: ['ticket', ticket.id, 'analysis'],
        }),
        queryClient.invalidateQueries({ queryKey: ['analysis'] }),
        queryClient.invalidateQueries({
          queryKey: ['ticket', ticket.id, 'events'],
        }),
        queryClient.invalidateQueries({ queryKey: ['tickets'] }),
        queryClient.invalidateQueries({ queryKey: ['dashboard'] }),
      ])
    },
  })

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setValidationError(null)
    const data = new FormData(event.currentTarget)
    const priority = data.get('priority')
    const reason = data.get('reason')
    if (!priority) {
      setValidationError('Select a priority.')
      return
    }
    if (typeof reason !== 'string' || reason.trim().length < 5) {
      setValidationError(
        'Provide at least 5 characters explaining the override.',
      )
      return
    }
    mutation.mutate({
      priority: priority as TicketPriority,
      reason: reason.trim(),
    })
  }

  return (
    <form className="priority-override" onSubmit={submit} noValidate>
      <div className="triage-title-row">
        <div>
          <p className="section-label">Human decision</p>
          <h3>Priority override</h3>
        </div>
        {ticket.priority_overridden && (
          <span className="badge badge--human">Human override</span>
        )}
      </div>
      {ticket.priority_overridden && ticket.priority_override_reason && (
        <p className="override-current">
          <strong>Current reason:</strong> {ticket.priority_override_reason}
        </p>
      )}
      <div className="override-fields">
        <div className="field">
          <label htmlFor="override-priority">Priority</label>
          <select id="override-priority" name="priority" defaultValue="">
            <option value="" disabled>
              Select P1-P4
            </option>
            <option value="p1">P1 - Critical</option>
            <option value="p2">P2 - High</option>
            <option value="p3">P3 - Medium</option>
            <option value="p4">P4 - Low</option>
          </select>
        </div>
        <div className="field field--reason">
          <label htmlFor="override-reason">Reason</label>
          <input
            id="override-reason"
            name="reason"
            minLength={5}
            maxLength={500}
            placeholder="Operational impact or service context"
          />
        </div>
        <button
          className="button button--outline"
          disabled={mutation.isPending}
        >
          {mutation.isPending ? 'Applying...' : 'Apply override'}
        </button>
      </div>
      {(validationError || mutation.error) && (
        <p className="form-error" role="alert">
          {validationError ?? mutation.error?.message}
        </p>
      )}
    </form>
  )
}
