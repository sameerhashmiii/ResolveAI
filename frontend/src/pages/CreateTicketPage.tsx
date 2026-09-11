import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { createTicket } from '../api/tickets'
import type { CreateTicketInput } from '../api/types'
import { useAuth } from '../auth/AuthContext'

const requiredFields = ['title', 'description', 'requester_name'] as const

function formValue(data: FormData, field: string) {
  const value = data.get(field)
  return typeof value === 'string' ? value.trim() : ''
}

export function CreateTicketPage() {
  const { csrfToken } = useAuth()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [errors, setErrors] = useState<Record<string, string>>({})

  const mutation = useMutation({
    mutationFn: (input: CreateTicketInput) => {
      if (!csrfToken)
        throw new Error(
          'Your session is missing a security token. Please sign in again.',
        )
      return createTicket(input, csrfToken)
    },
    onSuccess: (ticket) => {
      void queryClient.invalidateQueries({ queryKey: ['tickets'] })
      void queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      void navigate(`/tickets/${ticket.id}`)
    },
  })

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const data = new FormData(event.currentTarget)
    const nextErrors: Record<string, string> = {}
    requiredFields.forEach((field) => {
      if (!formValue(data, field)) nextErrors[field] = 'This field is required.'
    })
    if (formValue(data, 'title').length > 160)
      nextErrors.title = 'Use 160 characters or fewer.'
    setErrors(nextErrors)
    if (Object.keys(nextErrors).length) return

    const value = (field: string) => formValue(data, field)
    const optional = (field: string) => {
      const fieldValue = value(field)
      return fieldValue ? { [field]: fieldValue } : {}
    }
    const input: CreateTicketInput = {
      title: value('title'),
      description: value('description'),
      requester_name: value('requester_name'),
      ...optional('requester_department'),
      ...optional('location'),
      ...optional('device'),
      ...optional('application'),
    }
    mutation.mutate(input)
  }

  return (
    <div className="page page--narrow">
      <Link className="back-link" to="/tickets">
        ← Back to tickets
      </Link>
      <header className="page-header">
        <p className="eyebrow">Structured intake</p>
        <h1>Create a service request.</h1>
        <p>
          Capture the issue and its environment so the right person can begin
          with context.
        </p>
      </header>
      <form className="ticket-form content-card" onSubmit={submit} noValidate>
        <fieldset>
          <legend>Request</legend>
          <div className="field field--wide">
            <label htmlFor="title">
              Title <span>*</span>
            </label>
            <input
              id="title"
              name="title"
              maxLength={160}
              aria-invalid={Boolean(errors.title)}
              aria-describedby={errors.title ? 'title-error' : undefined}
            />
            {errors.title && (
              <small className="field-error" id="title-error">
                {errors.title}
              </small>
            )}
          </div>
          <div className="field field--wide">
            <label htmlFor="description">
              Description <span>*</span>
            </label>
            <textarea
              id="description"
              name="description"
              rows={7}
              aria-invalid={Boolean(errors.description)}
              aria-describedby={
                errors.description ? 'description-error' : undefined
              }
            />
            {errors.description && (
              <small className="field-error" id="description-error">
                {errors.description}
              </small>
            )}
            <small>
              Include what happened, when it started, and any impact.
            </small>
          </div>
        </fieldset>
        <fieldset>
          <legend>Requester and environment</legend>
          <div className="field">
            <label htmlFor="requester_name">
              Requester name <span>*</span>
            </label>
            <input
              id="requester_name"
              name="requester_name"
              aria-invalid={Boolean(errors.requester_name)}
              aria-describedby={
                errors.requester_name ? 'requester-error' : undefined
              }
            />
            {errors.requester_name && (
              <small className="field-error" id="requester-error">
                {errors.requester_name}
              </small>
            )}
          </div>
          <div className="field">
            <label htmlFor="requester_department">Department</label>
            <input id="requester_department" name="requester_department" />
          </div>
          <div className="field">
            <label htmlFor="location">Location</label>
            <input id="location" name="location" />
          </div>
          <div className="field">
            <label htmlFor="device">Device</label>
            <input id="device" name="device" />
          </div>
          <div className="field field--wide">
            <label htmlFor="application">Application</label>
            <input id="application" name="application" />
          </div>
        </fieldset>
        {mutation.isError && (
          <p className="form-error" role="alert">
            {mutation.error.message}
          </p>
        )}
        <div className="form-actions">
          <Link className="button button--quiet" to="/tickets">
            Cancel
          </Link>
          <button
            className="button button--primary"
            disabled={mutation.isPending}
          >
            {mutation.isPending ? 'Creating ticket...' : 'Create ticket'}
          </button>
        </div>
      </form>
    </div>
  )
}
