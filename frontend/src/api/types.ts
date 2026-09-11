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
