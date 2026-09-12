import { useState, type FormEvent } from 'react'

import type { Recommendation } from '../../api/types'
import { formValue } from './formValue'

interface Props {
  recommendation: Recommendation | null
  isManager: boolean
  disabled: boolean
  pending: boolean
  onDecision: (input: {
    decision: 'approve' | 'reject' | 'modify'
    reason: string
    modified_instructions?: string
  }) => void
}

export function RecommendationPanel({
  recommendation,
  isManager,
  disabled,
  pending,
  onDecision,
}: Props) {
  const [decision, setDecision] = useState<
    'approve' | 'reject' | 'modify' | null
  >(null)
  const [error, setError] = useState<string | null>(null)

  if (!recommendation)
    return (
      <div className="resolution-state">
        <h3>No recommendation available</h3>
        <p>The completed assessment has not produced a recommendation yet.</p>
      </div>
    )

  const highImpact = recommendation.action_type === 'high_impact'
  const managerBlocked = highImpact && !isManager
  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!decision) return
    const data = new FormData(event.currentTarget)
    const reason = formValue(data, 'decision_reason')
    const instructions = formValue(data, 'modified_instructions')
    if (reason.length < 5) {
      setError('Provide at least 5 characters explaining the decision.')
      return
    }
    if (
      decision === 'modify' &&
      (instructions.length < 10 || instructions.length > 1000)
    ) {
      setError('Modified instructions must be between 10 and 1000 characters.')
      return
    }
    setError(null)
    onDecision({
      decision,
      reason,
      ...(decision === 'modify' ? { modified_instructions: instructions } : {}),
    })
  }

  return (
    <div className="resolution-block">
      <div className="resolution-block-heading">
        <div>
          <p className="section-label">AI recommendation</p>
          <h3>{recommendation.title}</h3>
        </div>
        <span className={`badge badge--${recommendation.status}`}>
          {recommendation.status}
        </span>
      </div>
      <p className="execution-warning">
        This AI recommendation has not executed any action. A human decision is
        required before the workflow can continue.
      </p>
      {highImpact && (
        <div className="approval-warning" role="note">
          <strong>Human approval required</strong>
          <span>This high-impact action requires Manager approval.</span>
          {managerBlocked && (
            <span>Your analyst role cannot approve or modify this action.</span>
          )}
        </div>
      )}
      <dl className="resolution-details">
        <div>
          <dt>Action type</dt>
          <dd>{recommendation.action_type.replaceAll('_', ' ')}</dd>
        </div>
        <div>
          <dt>Instructions</dt>
          <dd>{recommendation.instructions}</dd>
        </div>
      </dl>
      {recommendation.action_type.toLowerCase().includes('escalat') && (
        <p className="advisory-note">
          Escalation is advisory until you use the explicit Escalate ticket
          action below.
        </p>
      )}
      {recommendation.status === 'proposed' && !disabled && (
        <form className="decision-form" onSubmit={submit}>
          <div
            className="decision-actions"
            aria-label="Recommendation decision"
          >
            <button
              className="button button--primary"
              type="button"
              disabled={pending || managerBlocked}
              onClick={() => setDecision('approve')}
            >
              Approve
            </button>
            <button
              className="button button--outline"
              type="button"
              disabled={pending}
              onClick={() => setDecision('reject')}
            >
              Reject
            </button>
            <button
              className="button button--outline"
              type="button"
              disabled={pending || managerBlocked}
              onClick={() => setDecision('modify')}
            >
              Modify
            </button>
          </div>
          {decision && (
            <>
              <div className="field">
                <label htmlFor="decision-reason">Decision reason</label>
                <textarea id="decision-reason" name="decision_reason" />
              </div>
              {decision === 'modify' && (
                <div className="field">
                  <label htmlFor="modified-instructions">
                    Modified instructions
                  </label>
                  <textarea
                    id="modified-instructions"
                    name="modified_instructions"
                    defaultValue={recommendation.instructions}
                    maxLength={1000}
                  />
                </div>
              )}
              {error && (
                <p className="form-error" role="alert">
                  {error}
                </p>
              )}
              <button className="button button--primary" disabled={pending}>
                {pending ? 'Recording decision...' : `Confirm ${decision}`}
              </button>
            </>
          )}
        </form>
      )}
    </div>
  )
}
