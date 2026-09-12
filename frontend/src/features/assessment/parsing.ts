import type {
  Assessment,
  AssessmentEvidence,
  AssessmentExplanation,
  AssessmentInference,
  AssessmentRecommendation,
  AssessmentStatus,
  ConfidenceFactor,
  ExplanationTimelineItem,
} from '../../api/types'

const statuses: AssessmentStatus[] = [
  'queued',
  'running',
  'completed',
  'failed',
  'timed_out',
  'timedout',
]

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null

const isStringArray = (value: unknown): value is string[] =>
  Array.isArray(value) && value.every((item) => typeof item === 'string')

const isAssessmentStatus = (value: unknown): value is AssessmentStatus =>
  typeof value === 'string' && statuses.some((status) => status === value)

function parseList<T>(
  value: unknown,
  parser: (item: unknown) => T | null,
): T[] | null {
  if (!Array.isArray(value)) return null
  const parsed = value.map(parser)
  return parsed.every((item): item is T => item !== null) ? parsed : null
}

function parseNullableString(value: unknown) {
  return typeof value === 'string' || value === null ? value : undefined
}

export function parseEvidence(value: unknown): AssessmentEvidence | null {
  if (!isRecord(value)) return null
  const relevance = value.relevance_score
  if (
    typeof value.id !== 'string' ||
    typeof value.evidence_type !== 'string' ||
    typeof value.source_id !== 'string' ||
    typeof value.title !== 'string' ||
    typeof value.excerpt !== 'string' ||
    (typeof value.supports !== 'string' && value.supports !== null) ||
    (typeof relevance !== 'number' && relevance !== null) ||
    !isRecord(value.metadata) ||
    typeof value.display_order !== 'number'
  )
    return null
  if (typeof relevance === 'number' && (relevance < 0 || relevance > 1))
    return null
  return {
    id: value.id,
    evidence_type: value.evidence_type,
    source_id: value.source_id,
    title: value.title,
    excerpt: value.excerpt,
    supports: value.supports,
    relevance_score: relevance,
    metadata: value.metadata,
    display_order: value.display_order,
  }
}

export function parseFactor(value: unknown): ConfidenceFactor | null {
  if (!isRecord(value)) return null
  const sourceIds = value.source_ids
  if (
    typeof value.key !== 'string' ||
    typeof value.label !== 'string' ||
    typeof value.weight !== 'number' ||
    !Number.isFinite(value.weight) ||
    typeof value.applied !== 'boolean' ||
    !isStringArray(sourceIds)
  )
    return null
  return {
    key: value.key,
    label: value.label,
    weight: value.weight,
    applied: value.applied,
    source_ids: sourceIds,
  }
}

function parseTimeline(value: unknown): ExplanationTimelineItem | null {
  if (
    !isRecord(value) ||
    typeof value.label !== 'string' ||
    typeof value.status !== 'string' ||
    typeof value.source_count !== 'number'
  )
    return null
  return {
    label: value.label,
    status: value.status,
    source_count: value.source_count,
  }
}

function parseInference(
  value: unknown,
): AssessmentInference | null | undefined {
  if (value === null) return null
  if (
    !isRecord(value) ||
    value.kind !== 'probable' ||
    typeof value.summary !== 'string'
  )
    return undefined
  return { kind: 'probable', summary: value.summary }
}

function parseRecommendation(
  value: unknown,
): AssessmentRecommendation | null | undefined {
  if (value === null) return null
  if (
    !isRecord(value) ||
    value.kind !== 'recommendation' ||
    typeof value.text !== 'string'
  )
    return undefined
  return { kind: 'recommendation', text: value.text }
}

export function parseAssessment(value: unknown): Assessment | null {
  if (!isRecord(value)) return null
  const evidence = parseList(value.observed_evidence, parseEvidence)
  const confidence = value.confidence
  const factors = isRecord(confidence)
    ? parseList(confidence.factors, parseFactor)
    : null
  const inference = parseInference(value.inference)
  const recommendation = parseRecommendation(value.recommendation)
  const escalation = value.escalation
  const model = parseNullableString(value.model)
  const errorCode = parseNullableString(value.error_code)
  const startedAt = parseNullableString(value.started_at)
  const completedAt = parseNullableString(value.completed_at)
  const limitations = value.limitations
  if (
    typeof value.id !== 'string' ||
    typeof value.ticket_id !== 'string' ||
    typeof value.investigation_id !== 'string' ||
    !isAssessmentStatus(value.status) ||
    typeof value.workflow_version !== 'string' ||
    typeof value.provider !== 'string' ||
    model === undefined ||
    typeof value.mode !== 'string' ||
    typeof value.mode_label !== 'string' ||
    evidence === null ||
    inference === undefined ||
    recommendation === undefined ||
    !isRecord(confidence) ||
    (typeof confidence.score !== 'number' && confidence.score !== null) ||
    (typeof confidence.score === 'number' &&
      (!Number.isFinite(confidence.score) ||
        confidence.score < 0 ||
        confidence.score > 1)) ||
    typeof confidence.version !== 'string' ||
    factors === null ||
    typeof confidence.description !== 'string' ||
    !isRecord(escalation) ||
    typeof escalation.required !== 'boolean' ||
    typeof escalation.threshold !== 'number' ||
    !Number.isFinite(escalation.threshold) ||
    escalation.threshold < 0 ||
    escalation.threshold > 1 ||
    typeof escalation.reason !== 'string' ||
    !isStringArray(limitations) ||
    errorCode === undefined ||
    startedAt === undefined ||
    completedAt === undefined ||
    (typeof value.duration_ms !== 'number' && value.duration_ms !== null) ||
    typeof value.created_at !== 'string'
  )
    return null

  return {
    id: value.id,
    ticket_id: value.ticket_id,
    investigation_id: value.investigation_id,
    status: value.status,
    workflow_version: value.workflow_version,
    provider: value.provider,
    model,
    mode: value.mode,
    mode_label: value.mode_label,
    observed_evidence: evidence,
    inference,
    confidence: {
      score: confidence.score,
      version: confidence.version,
      factors,
      description: confidence.description,
    },
    recommendation,
    limitations,
    escalation: {
      required: escalation.required,
      threshold: escalation.threshold,
      reason: escalation.reason,
    },
    error_code: errorCode,
    started_at: startedAt,
    completed_at: completedAt,
    duration_ms: value.duration_ms,
    created_at: value.created_at,
  }
}

export function parseExplanation(value: unknown): AssessmentExplanation | null {
  if (!isRecord(value) || !isRecord(value.assessment)) return null
  const timeline = parseList(value.investigation_timeline, parseTimeline)
  const evidence = parseList(value.supporting_evidence, parseEvidence)
  const factors = parseList(value.confidence_factors, parseFactor)
  if (
    timeline === null ||
    evidence === null ||
    factors === null ||
    typeof value.reasoning_disclosure !== 'string'
  )
    return null
  return {
    assessment: value.assessment,
    investigation_timeline: timeline,
    supporting_evidence: evidence,
    confidence_factors: factors,
    reasoning_disclosure: value.reasoning_disclosure,
  }
}
