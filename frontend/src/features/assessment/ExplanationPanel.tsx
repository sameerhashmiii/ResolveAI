import { useQuery } from '@tanstack/react-query'

import { getAssessmentExplanation } from '../../api/assessments'
import { EvidenceCards } from './EvidenceCards'
import { parseExplanation } from './parsing'

function signedWeight(weight: number) {
  return `${weight >= 0 ? '+' : ''}${weight.toFixed(2)}`
}

export function ExplanationPanel({ assessmentId }: { assessmentId: string }) {
  const raw = useQuery({
    queryKey: ['assessment', assessmentId, 'explanation'],
    queryFn: ({ signal }) => getAssessmentExplanation(assessmentId, signal),
  })
  const explanation = parseExplanation(raw.data)

  if (raw.isPending)
    return (
      <div className="assessment-explanation-state" role="status">
        Loading explanation...
      </div>
    )
  if (raw.isError)
    return (
      <div className="assessment-explanation-state form-error" role="alert">
        <p>Explanation could not be loaded. {raw.error.message}</p>
        <button
          className="button button--outline"
          type="button"
          onClick={() => void raw.refetch()}
        >
          Retry explanation
        </button>
      </div>
    )
  if (!explanation)
    return (
      <div className="assessment-explanation-state form-error" role="alert">
        Explanation unavailable because the service returned an invalid
        response.
      </div>
    )

  return (
    <div className="assessment-explanation-body">
      <section aria-labelledby="assessment-timeline-title">
        <h4 id="assessment-timeline-title">Investigation Timeline</h4>
        <ol className="explanation-timeline">
          {explanation.investigation_timeline.map((item, index) => (
            <li key={`${item.label}-${String(index)}`}>
              <strong>{item.label}</strong>
              <span>
                {item.status.replaceAll('_', ' ')} · {item.source_count} source
                {item.source_count === 1 ? '' : 's'}
              </span>
            </li>
          ))}
        </ol>
      </section>
      <section aria-labelledby="supporting-evidence-title">
        <h4 id="supporting-evidence-title">Supporting Evidence</h4>
        <EvidenceCards evidence={explanation.supporting_evidence} />
      </section>
      <section aria-labelledby="confidence-factors-title">
        <h4 id="confidence-factors-title">Confidence Factors</h4>
        <ul className="confidence-factors">
          {explanation.confidence_factors.map((factor) => (
            <li key={factor.key}>
              <span>
                <strong>{factor.label}</strong>
                <small>{factor.key}</small>
                {factor.source_ids.length > 0 && (
                  <small>{factor.source_ids.join(', ')}</small>
                )}
              </span>
              <span>{factor.applied ? 'Applied' : 'Not applied'}</span>
              <strong>{signedWeight(factor.weight)}</strong>
            </li>
          ))}
        </ul>
      </section>
      <p className="reasoning-disclosure">{explanation.reasoning_disclosure}</p>
    </div>
  )
}
