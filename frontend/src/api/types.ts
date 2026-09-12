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
  status?: 'new' | 'in_progress' | 'resolved' | 'escalated'
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
