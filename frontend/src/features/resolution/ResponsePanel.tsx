import { useEffect, useState, type FormEvent } from 'react'

import type { SupportResponse } from '../../api/types'
import { formValue } from './formValue'

interface Props {
  response: SupportResponse | null
  canGenerate: boolean
  disabled: boolean
  pending: boolean
  onGenerate: () => void
  onSave: (body: string) => void
  onApprove: (body: string) => void
  onReject: (reason: string) => void
}

export function ResponsePanel({
  response,
  canGenerate,
  disabled,
  pending,
  onGenerate,
  onSave,
  onApprove,
  onReject,
}: Props) {
  const [draft, setDraft] = useState(response?.draft_body ?? '')
  const [rejecting, setRejecting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  useEffect(() => setDraft(response?.draft_body ?? ''), [response])

  const reject = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const reason = formValue(
      new FormData(event.currentTarget),
      'response_rejection_reason',
    )
    if (reason.length < 5) {
      setError('Provide at least 5 characters explaining the rejection.')
      return
    }
    setError(null)
    onReject(reason)
  }
  const save = () => {
    if (draft.trim().length < 20) {
      setError('The response draft must contain at least 20 characters.')
      return
    }
    setError(null)
    onSave(draft)
  }

  return (
    <div className="resolution-block">
      <p className="section-label">Requester communication</p>
      <h3>Requester response</h3>
      {!response && canGenerate && !disabled && (
        <button
          className="button button--primary"
          disabled={pending}
          onClick={onGenerate}
        >
          {pending ? 'Generating response...' : 'Generate requester response'}
        </button>
      )}
      {!response && !canGenerate && (
        <p className="muted">
          Approve or modify the recommendation before generating a draft.
        </p>
      )}
      {response && (
        <>
          <span className={`badge badge--${response.status}`}>
            {response.status}
          </span>
          <div className="field response-editor">
            <label htmlFor="customer-response">
              Professional response draft
            </label>
            <textarea
              id="customer-response"
              value={draft}
              disabled={disabled || response.status !== 'draft'}
              onChange={(event) => setDraft(event.target.value)}
            />
          </div>
          <p className="delivery-note">
            Approving this response does not send it. ResolveAI has no delivery
            adapter.
          </p>
          {response.status === 'draft' && !disabled && (
            <div className="response-actions">
              <button
                className="button button--outline"
                disabled={pending}
                onClick={save}
              >
                Save draft
              </button>
              <button
                className="button button--primary"
                disabled={pending || draft.trim().length < 20}
                onClick={() => onApprove(draft)}
              >
                Approve response
              </button>
              <button
                className="button button--quiet"
                disabled={pending}
                onClick={() => setRejecting(true)}
              >
                Reject response
              </button>
            </div>
          )}
          {error && !rejecting && (
            <p className="form-error" role="alert">
              {error}
            </p>
          )}
          {rejecting && response.status === 'draft' && !disabled && (
            <form className="decision-form" onSubmit={reject}>
              <div className="field">
                <label htmlFor="response-rejection-reason">
                  Rejection reason
                </label>
                <textarea
                  id="response-rejection-reason"
                  name="response_rejection_reason"
                />
              </div>
              {error && (
                <p className="form-error" role="alert">
                  {error}
                </p>
              )}
              <button className="button button--outline" disabled={pending}>
                Confirm response rejection
              </button>
            </form>
          )}
        </>
      )}
    </div>
  )
}
