import type { AssessmentEvidence } from '../../api/types'

export function EvidenceCards({
  evidence,
}: {
  evidence: AssessmentEvidence[]
}) {
  return evidence.length === 0 ? (
    <p className="observation-unavailable">No supporting evidence returned.</p>
  ) : (
    <div className="assessment-evidence-grid">
      {[...evidence]
        .sort((left, right) => left.display_order - right.display_order)
        .map((item) => (
          <article className="assessment-evidence" key={item.id}>
            <div className="assessment-source-line">
              <span>{item.source_id}</span>
              <span>{item.evidence_type.replaceAll('_', ' ')}</span>
            </div>
            <h4>{item.title}</h4>
            <p>{item.excerpt}</p>
            {item.supports && (
              <p className="assessment-supports">
                <strong>Supports:</strong> {item.supports}
              </p>
            )}
            {item.relevance_score !== null && (
              <small>Relevance {Math.round(item.relevance_score * 100)}%</small>
            )}
          </article>
        ))}
    </div>
  )
}
