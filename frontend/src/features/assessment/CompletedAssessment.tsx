import { useState } from 'react'

import type { Assessment } from '../../api/types'
import { EvidenceCards } from './EvidenceCards'
import { ExplanationPanel } from './ExplanationPanel'

export function CompletedAssessment({
  assessment,
}: {
  assessment: Assessment
}) {
  const [showWhy, setShowWhy] = useState(false)
  if (
    !assessment.inference ||
    !assessment.recommendation ||
    assessment.confidence.score === null
  )
    return (
      <div className="assessment-state assessment-state--error" role="alert">
        Assessment unavailable because completed results were incomplete.
      </div>
    )
  const explanationId = `assessment-explanation-${assessment.id}`

  return (
    <div className="assessment-results">
      <div className="assessment-mode">{assessment.mode_label}</div>
      <section
        className="assessment-block"
        aria-labelledby="observed-evidence-title"
      >
        <p className="assessment-index">01</p>
        <h3 id="observed-evidence-title">Observed Evidence</h3>
        <EvidenceCards evidence={assessment.observed_evidence} />
      </section>
      <section
        className="assessment-block assessment-inference"
        aria-labelledby="root-cause-title"
      >
        <p className="assessment-index">02</p>
        <div className="assessment-block-heading">
          <h3 id="root-cause-title">Probable Root Cause</h3>
          <span className="badge badge--inference">
            AI inference - not confirmed
          </span>
        </div>
        <p>{assessment.inference.summary}</p>
      </section>
      <section
        className="assessment-block assessment-confidence"
        aria-labelledby="confidence-title"
      >
        <p className="assessment-index">03</p>
        <h3 id="confidence-title">Evidence confidence</h3>
        <strong>{Math.round(assessment.confidence.score * 100)}%</strong>
        <p>
          Evidence confidence in this recommendation, not measured accuracy.
        </p>
        <small>{assessment.confidence.description}</small>
      </section>
      <section
        className="assessment-block assessment-recommendation"
        aria-labelledby="recommendation-title"
      >
        <p className="assessment-index">04</p>
        <div className="assessment-block-heading">
          <h3 id="recommendation-title">Recommended Action</h3>
          <span className="badge badge--review">
            Recommendation - human review required
          </span>
        </div>
        <p>{assessment.recommendation.text}</p>
        <small>No action has been executed.</small>
      </section>
      {assessment.limitations.length > 0 && (
        <section
          className="assessment-limitations"
          aria-labelledby="limitations-title"
        >
          <h3 id="limitations-title">Limitations</h3>
          <ul>
            {assessment.limitations.map((limitation) => (
              <li key={limitation}>{limitation}</li>
            ))}
          </ul>
        </section>
      )}
      {assessment.escalation.required && (
        <div className="assessment-warning" role="alert">
          <strong>
            Evidence confidence is low. Human investigation recommended.
          </strong>
          {assessment.escalation.reason && (
            <p>{assessment.escalation.reason}</p>
          )}
          <small>
            Escalation threshold{' '}
            {Math.round(assessment.escalation.threshold * 100)}%
          </small>
        </div>
      )}
      <button
        className="button button--why"
        type="button"
        aria-expanded={showWhy}
        aria-controls={explanationId}
        onClick={() => setShowWhy((visible) => !visible)}
      >
        {showWhy ? 'Hide Why' : 'Show Me Why'}
      </button>
      {showWhy && (
        <aside
          className="assessment-explanation"
          id={explanationId}
          aria-labelledby={`${explanationId}-title`}
        >
          <div className="assessment-explanation-heading">
            <div>
              <p className="section-label">Persisted rationale</p>
              <h3 id={`${explanationId}-title`}>Why this assessment?</h3>
            </div>
            <button
              className="button button--outline"
              type="button"
              onClick={() => setShowWhy(false)}
              autoFocus
            >
              Close
            </button>
          </div>
          <ExplanationPanel assessmentId={assessment.id} />
        </aside>
      )}
    </div>
  )
}
