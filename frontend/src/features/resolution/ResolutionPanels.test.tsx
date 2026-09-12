import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import type {
  Recommendation,
  SupportResponse,
  TicketDetail,
} from '../../api/types'
import { RecommendationPanel } from './RecommendationPanel'
import { ResponsePanel } from './ResponsePanel'
import { TerminalActions } from './TerminalActions'

const recommendation: Recommendation = {
  id: 'rec-1',
  ticket_id: 'ticket-1',
  assessment_id: 'assessment-1',
  title: 'Reset VPN profile',
  original_instructions: 'Reset the VPN profile safely.',
  instructions: 'Reset the VPN profile safely.',
  action_type: 'troubleshoot',
  requires_approval: true,
  status: 'proposed',
  decided_by_id: null,
  decision_reason: null,
  decided_at: null,
  created_at: '2026-09-11T10:00:00Z',
  updated_at: '2026-09-11T10:00:00Z',
}
const response: SupportResponse = {
  id: 'response-1',
  ticket_id: 'ticket-1',
  assessment_id: 'assessment-1',
  recommendation_id: 'rec-1',
  generated_by: 'ai',
  provider: 'demo',
  model: null,
  mode: 'local_demo',
  draft_body:
    'Hello Jordan, based on evidence, the VPN issue appears to need review.',
  final_body: null,
  status: 'draft',
  created_by_id: 'user-1',
  approved_by_id: null,
  rejected_by_id: null,
  rejection_reason: null,
  approved_at: null,
  rejected_at: null,
  created_at: '2026-09-11T10:00:00Z',
  updated_at: '2026-09-11T10:00:00Z',
  approval_semantics: 'approval_only_not_sent',
}
const ticket = {
  id: 'ticket-1',
  ticket_number: 'RAI-1',
  title: 'VPN issue',
  description: 'Cannot connect',
  requester_name: 'Jordan',
  category: 'vpn',
  priority: 'p2',
  status: 'in_progress',
  assigned_to: null,
  created_by: { id: 'user-1', display_name: 'Alex' },
  created_at: '2026-09-11T10:00:00Z',
  updated_at: '2026-09-11T10:00:00Z',
} satisfies TicketDetail

describe('resolution panels', () => {
  it('offers generation only after an accepted recommendation', () => {
    const { rerender } = render(
      <ResponsePanel
        response={null}
        canGenerate={false}
        disabled={false}
        pending={false}
        onGenerate={vi.fn()}
        onSave={vi.fn()}
        onApprove={vi.fn()}
        onReject={vi.fn()}
      />,
    )
    expect(
      screen.queryByRole('button', { name: 'Generate customer response' }),
    ).not.toBeInTheDocument()
    rerender(
      <ResponsePanel
        response={null}
        canGenerate
        disabled={false}
        pending={false}
        onGenerate={vi.fn()}
        onSave={vi.fn()}
        onApprove={vi.fn()}
        onReject={vi.fn()}
      />,
    )
    expect(
      screen.getByRole('button', { name: 'Generate customer response' }),
    ).toBeInTheDocument()
  })

  it.each([
    ['approve', 'Approve'],
    ['reject', 'Reject'],
  ] as const)('requires a reason and submits %s', async (decision, label) => {
    const user = userEvent.setup()
    const onDecision = vi.fn()
    render(
      <RecommendationPanel
        recommendation={recommendation}
        isManager
        disabled={false}
        pending={false}
        onDecision={onDecision}
      />,
    )
    expect(screen.getByText(/has not executed any action/i)).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: label }))
    await user.click(
      screen.getByRole('button', { name: `Confirm ${decision}` }),
    )
    expect(screen.getByRole('alert')).toHaveTextContent('at least 5 characters')
    await user.type(
      screen.getByLabelText('Decision reason'),
      'Reviewed by human',
    )
    await user.click(
      screen.getByRole('button', { name: `Confirm ${decision}` }),
    )
    expect(onDecision).toHaveBeenCalledWith({
      decision,
      reason: 'Reviewed by human',
    })
  })

  it('submits modified instructions and gates high-impact approval to managers', async () => {
    const user = userEvent.setup()
    const onDecision = vi.fn()
    const { rerender } = render(
      <RecommendationPanel
        recommendation={{ ...recommendation, action_type: 'high_impact' }}
        isManager={false}
        disabled={false}
        pending={false}
        onDecision={onDecision}
      />,
    )
    expect(screen.getByText('Human approval required')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Approve' })).toBeDisabled()
    expect(screen.getByText(/analyst role cannot approve/i)).toBeInTheDocument()
    rerender(
      <RecommendationPanel
        recommendation={recommendation}
        isManager
        disabled={false}
        pending={false}
        onDecision={onDecision}
      />,
    )
    await user.click(screen.getByRole('button', { name: 'Modify' }))
    await user.clear(screen.getByLabelText('Modified instructions'))
    await user.type(
      screen.getByLabelText('Modified instructions'),
      'Reset only after identity verification.',
    )
    await user.type(
      screen.getByLabelText('Decision reason'),
      'Reduced account risk',
    )
    await user.click(screen.getByRole('button', { name: 'Confirm modify' }))
    expect(onDecision).toHaveBeenCalledWith({
      decision: 'modify',
      reason: 'Reduced account risk',
      modified_instructions: 'Reset only after identity verification.',
    })
  })

  it('edits, saves, approves, and rejects a draft without claiming delivery', async () => {
    const user = userEvent.setup()
    const onSave = vi.fn()
    const onApprove = vi.fn()
    const onReject = vi.fn()
    render(
      <ResponsePanel
        response={response}
        canGenerate
        disabled={false}
        pending={false}
        onGenerate={vi.fn()}
        onSave={onSave}
        onApprove={onApprove}
        onReject={onReject}
      />,
    )
    const editor = screen.getByLabelText('Professional response draft')
    await user.clear(editor)
    await user.type(editor, 'Updated professional response')
    await user.click(screen.getByRole('button', { name: 'Save draft' }))
    expect(onSave).toHaveBeenCalledWith('Updated professional response')
    await user.click(screen.getByRole('button', { name: 'Approve response' }))
    expect(onApprove).toHaveBeenCalledWith('Updated professional response')
    expect(screen.getByText(/Approving this response/i)).toHaveTextContent(
      /does not send/i,
    )
    expect(screen.queryByText(/^sent$/i)).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Reject response' }))
    await user.type(
      screen.getByLabelText('Rejection reason'),
      'Needs more detail',
    )
    await user.click(
      screen.getByRole('button', { name: 'Confirm response rejection' }),
    )
    expect(onReject).toHaveBeenCalledWith('Needs more detail')
  })

  it('allows resolve only with an approved response and captures escalation fields', async () => {
    const user = userEvent.setup()
    const onResolve = vi.fn()
    const onEscalate = vi.fn()
    const { rerender } = render(
      <TerminalActions
        ticket={ticket}
        response={response}
        pending={false}
        onResolve={onResolve}
        onEscalate={onEscalate}
      />,
    )
    expect(
      screen.queryByLabelText('Resolution summary'),
    ).not.toBeInTheDocument()
    rerender(
      <TerminalActions
        ticket={ticket}
        response={{ ...response, status: 'approved' }}
        pending={false}
        onResolve={onResolve}
        onEscalate={onEscalate}
      />,
    )
    await user.type(
      screen.getByLabelText('Resolution summary'),
      'VPN access restored',
    )
    await user.click(screen.getByRole('button', { name: 'Resolve ticket' }))
    expect(onResolve).toHaveBeenCalledWith('VPN access restored')
    await user.type(screen.getByLabelText('Destination'), 'Network operations')
    await user.type(
      screen.getByLabelText('Reason'),
      'Gateway investigation required',
    )
    await user.click(
      screen.getByRole('button', {
        name: /Escalate ticket with confirmation/i,
      }),
    )
    expect(onEscalate).toHaveBeenCalledWith(
      'Network operations',
      'Gateway investigation required',
    )
  })

  it('renders terminal metadata and disables terminal forms', () => {
    render(
      <TerminalActions
        ticket={{
          ...ticket,
          status: 'escalated',
          escalated_at: '2026-09-11T12:00:00Z',
          escalation_destination: 'Security',
          escalation_reason: 'Potential compromise',
        }}
        response={null}
        pending={false}
        onResolve={vi.fn()}
        onEscalate={vi.fn()}
      />,
    )
    expect(
      screen.getByRole('heading', { name: 'Ticket escalated' }),
    ).toBeInTheDocument()
    expect(screen.getByText('Security')).toBeInTheDocument()
    expect(screen.getByText('Potential compromise')).toBeInTheDocument()
    expect(screen.queryByLabelText('Destination')).not.toBeInTheDocument()
  })
})
