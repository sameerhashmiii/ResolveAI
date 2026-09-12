export interface User {
  id: string
  email: string
  display_name: string
  role: string
  is_demo: boolean
}

export interface UserSummary {
  id: string
  email?: string
  display_name: string
  role?: string
}

export interface AuthResponse {
  user: User
  csrf_token: string
}

export interface TicketSummary {
  id: string
  ticket_number: string
  title: string
  description: string
  requester_name: string
  requester_department?: string | null
  location?: string | null
  device?: string | null
  application?: string | null
  category: string | null
  priority: string | null
  priority_overridden?: boolean
  priority_override_reason?: string | null
  status: string
  assigned_to: UserSummary | null
  created_by: UserSummary
  created_at: string
  updated_at: string
  resolved_at?: string | null
  resolution_summary?: string | null
  escalated_at?: string | null
  escalation_destination?: string | null
  escalation_reason?: string | null
}

export type TicketDetail = TicketSummary

export interface TicketEvent {
  id: string
  event_type: string
  summary: string
  actor: UserSummary | null
  created_at: string
}

export interface DashboardOverview {
  total_tickets: number
  open_tickets: number
  resolved_tickets: number
  escalated_tickets: number
  recent_tickets: TicketSummary[]
}

export interface PaginatedTickets {
  items: TicketSummary[]
  page: number
  page_size: number
  total: number
  has_next: boolean
}

export interface CreateTicketInput {
  title: string
  description: string
  requester_name: string
  requester_department?: string
  location?: string
  device?: string
  application?: string
  attachment_metadata?: unknown[]
}

export interface UpdateTicketInput {
  title?: string
  description?: string
  status?: 'new' | 'in_progress'
}

export type RecommendationStatus =
  'proposed' | 'approved' | 'modified' | 'rejected' | 'completed'

export interface Recommendation {
  id: string
  ticket_id: string
  assessment_id: string
  title: string
  original_instructions: string
  instructions: string
  action_type: string
  requires_approval: boolean
  status: RecommendationStatus
  decided_by_id: string | null
  decision_reason: string | null
  decided_at: string | null
  created_at: string
  updated_at: string
}

export type SupportResponseStatus = 'draft' | 'approved' | 'rejected'

export interface SupportResponse {
  id: string
  ticket_id: string
  assessment_id: string
  recommendation_id: string
  generated_by: string
  provider: string
  model: string | null
  mode: string
  draft_body: string
  final_body: string | null
  status: SupportResponseStatus
  created_by_id: string
  approved_by_id: string | null
  rejected_by_id: string | null
  rejection_reason: string | null
  approved_at: string | null
  rejected_at: string | null
  created_at: string
  updated_at: string
  approval_semantics: 'approval_only_not_sent'
}

export type TicketPriority = 'p1' | 'p2' | 'p3' | 'p4'

export type AnalysisStatus =
  'queued' | 'running' | 'completed' | 'failed' | 'timed_out'

export type AnalysisMode = 'local_demo' | 'hosted'

export type AnalysisEntityValue = string | string[] | null

export interface AnalysisEntities {
  user: AnalysisEntityValue
  location: AnalysisEntityValue
  application: AnalysisEntityValue
  device: AnalysisEntityValue
  issue_type: AnalysisEntityValue
  affected_scope: AnalysisEntityValue
  urgency: AnalysisEntityValue
}

export type AnalysisFactorValue = string | number | boolean | string[] | null

export interface Analysis {
  id: string
  ticket_id: string
  status: AnalysisStatus
  workflow_version: string
  provider: string
  model: string | null
  mode: AnalysisMode
  category: string | null
  category_confidence: number | null
  recommended_priority: TicketPriority | null
  validated_priority: TicketPriority | null
  entities: AnalysisEntities | null
  priority_factors: Record<string, AnalysisFactorValue> | string[] | null
  requires_manual_review: boolean
  error_code: string | null
  started_at: string | null
  completed_at: string | null
  duration_ms: number | null
  created_at: string
}

export interface AnalysisAccepted {
  analysis_id: string
  status: 'queued'
}

export interface PriorityOverrideInput {
  priority: TicketPriority
  reason: string
}

export type InvestigationStatus = AnalysisStatus

export interface InvestigationStep {
  id: string
  step_key: string
  step_order: number
  label: string
  tool_name: string | null
  status: string
  source_count: number
  duration_ms: number
  sanitized_inputs: Record<string, unknown>
  result: Record<string, unknown> | null
  created_at: string
}

export interface Investigation {
  id: string
  ticket_id: string
  analysis_id: string | null
  requested_by_id: string
  status: InvestigationStatus
  workflow_version: string
  reference_time: string
  reference_basis: 'ticket_created_at' | 'curated_demo_scenario'
  simulated_reference: boolean
  planned_tools: Array<Record<string, unknown>>
  limitations: string[]
  error_code: string | null
  started_at: string | null
  completed_at: string | null
  duration_ms: number | null
  created_at: string
  steps: InvestigationStep[]
}

export interface InvestigationAccepted {
  investigation_id: string
  status: 'queued'
}

export type AssessmentStatus =
  'queued' | 'running' | 'completed' | 'failed' | 'timed_out' | 'timedout'

export interface AssessmentEvidence {
  id: string
  evidence_type: string
  source_id: string
  title: string
  excerpt: string
  supports: string | null
  relevance_score: number | null
  metadata: Record<string, unknown>
  display_order: number
}

export interface AssessmentInference {
  kind: 'probable'
  summary: string
}

export interface AssessmentRecommendation {
  kind: 'recommendation'
  text: string
}

export interface ConfidenceFactor {
  key: string
  label: string
  weight: number
  applied: boolean
  source_ids: string[]
}

export interface AssessmentConfidence {
  score: number | null
  version: string
  factors: ConfidenceFactor[]
  description: string
}

export interface AssessmentEscalation {
  required: boolean
  threshold: number
  reason: string
}

export interface Assessment {
  id: string
  ticket_id: string
  investigation_id: string
  status: AssessmentStatus
  workflow_version: string
  provider: string
  model: string | null
  mode: string
  mode_label: string
  observed_evidence: AssessmentEvidence[]
  inference: AssessmentInference | null
  confidence: AssessmentConfidence
  recommendation: AssessmentRecommendation | null
  limitations: string[]
  escalation: AssessmentEscalation
  error_code: string | null
  started_at: string | null
  completed_at: string | null
  duration_ms: number | null
  created_at: string
}

export interface AssessmentAccepted {
  assessment_id: string
  status: 'queued'
}

export interface ExplanationTimelineItem {
  label: string
  status: string
  source_count: number
}

export interface AssessmentExplanation {
  assessment: Record<string, unknown>
  investigation_timeline: ExplanationTimelineItem[]
  supporting_evidence: AssessmentEvidence[]
  confidence_factors: ConfidenceFactor[]
  reasoning_disclosure: string
}

export interface SimilarTicket {
  source_id: string
  title: string
  description: string
  category: string | null
  priority: string | null
  status: string
  resolution: string | null
  resolution_time_minutes: number | null
  opened_at: string
  similarity: number
  incident_id: string | null
}

export interface SimilarTicketsResponse {
  items: SimilarTicket[]
}
