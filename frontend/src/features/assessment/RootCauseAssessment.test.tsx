import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type {
  Analysis,
  Assessment,
  AssessmentExplanation,
  Investigation,
  TicketDetail,
} from '../../api/types'
import {
  jsonResponse,
  renderApp,
  requestUrl,
  userResponse,
} from '../../test/renderApp'

afterEach(() => vi.restoreAllMocks())

const ticket: TicketDetail = {
  id: 'ticket-assessment',
  ticket_number: 'RAI-1070',
  title: 'Dallas name resolution failures',
  description: 'Multiple Dallas users cannot resolve internal services.',
  requester_name: 'Alex Rivera',
  category: 'network',
  priority: 'p1',
  status: 'new',
  assigned_to: null,
  created_by: userResponse.user,
  created_at: '2026-09-11T10:00:00Z',
  updated_at: '2026-09-11T10:00:00Z',
}

const analysis: Analysis = {
  id: 'analysis-1',
  ticket_id: ticket.id,
  status: 'completed',
  workflow_version: 'triage-v1',
  provider: 'resolveai-demo',
  model: null,
  mode: 'local_demo',
  category: 'network',
  category_confidence: 0.94,
  recommended_priority: 'p1',
  validated_priority: 'p1',
  entities: null,
  priority_factors: null,
  requires_manual_review: false,
  error_code: null,
  started_at: null,
  completed_at: '2026-09-11T10:00:01Z',
  duration_ms: 1000,
  created_at: '2026-09-11T10:00:00Z',
}

const investigation: Investigation = {
  id: 'investigation-1',
  ticket_id: ticket.id,
  analysis_id: analysis.id,
  requested_by_id: userResponse.user.id,
  status: 'completed',
  workflow_version: 'investigation-v1',
  reference_time: '2026-09-11T10:00:00Z',
  reference_basis: 'ticket_created_at',
  simulated_reference: false,
  planned_tools: [],
  limitations: [],
  error_code: null,
  started_at: null,
  completed_at: '2026-09-11T10:01:00Z',
  duration_ms: 500,
  created_at: '2026-09-11T10:00:00Z',
  steps: [],
}

const evidence = [
  {
    id: 'evidence-1',
    evidence_type: 'service_status',
    source_id: 'STATUS-DAL-7',
    title: 'Dallas DNS health',
    excerpt: 'DNS service in Dallas reports degraded health.',
    supports: 'Regional service degradation',
    relevance_score: 0.97,
    metadata: { internal_key: 'never display this metadata' },
    display_order: 1,
  },
  {
    id: 'evidence-2',
    evidence_type: 'telemetry',
    source_id: 'TEL-DAL-19',
    title: 'Resolver latency',
    excerpt: 'Resolver p95 latency reached 910 ms.',
    supports: 'Elevated resolver latency',
    relevance_score: 0.89,
    metadata: {},
    display_order: 2,
  },
]

const assessment: Assessment = {
  id: 'assessment-1',
  ticket_id: ticket.id,
  investigation_id: investigation.id,
  status: 'completed',
  workflow_version: 'assessment-v1',
  provider: 'resolveai-demo',
  model: null,
  mode: 'deterministic_demo',
  mode_label: 'Deterministic demo inference',
  observed_evidence: evidence,
  inference: {
    kind: 'probable',
    summary: 'Dallas DNS service degradation',
  },
  confidence: {
    score: 0.91,
    version: 'confidence-v1',
    description: 'Confidence in the recommendation, not measured accuracy.',
    factors: [
      {
        key: 'source_agreement',
        label: 'Service and telemetry agree',
        applied: true,
        weight: 0.24,
        source_ids: ['STATUS-DAL-7', 'TEL-DAL-19'],
      },
    ],
  },
  recommendation: {
    kind: 'recommendation',
    text: 'Review Dallas resolver health and failover readiness.',
  },
  limitations: ['The service report is regional, not device-specific.'],
  escalation: {
    required: false,
    threshold: 0.6,
    reason: 'Confidence meets the configured review threshold.',
  },
  error_code: null,
  started_at: null,
  completed_at: '2026-09-11T10:02:00Z',
  duration_ms: 400,
  created_at: '2026-09-11T10:01:00Z',
}

const explanation: AssessmentExplanation & Record<string, unknown> = {
  assessment: {
    id: assessment.id,
    mode_label: assessment.mode_label,
    internal_prompt: 'do not display nested assessment internals',
  },
  investigation_timeline: [
    {
      label: 'Checked Dallas service health',
      status: 'completed',
      source_count: 2,
    },
  ],
  supporting_evidence: evidence,
  confidence_factors: [
    {
      key: 'independent_sources',
      label: 'Independent sources agree',
      applied: true,
      weight: 0.31,
      source_ids: ['STATUS-DAL-7', 'TEL-DAL-19'],
    },
    {
      key: 'device_evidence',
      label: 'Device evidence available',
      applied: false,
      weight: -0.08,
      source_ids: [],
    },
  ],
  reasoning_disclosure:
    'Hidden chain-of-thought is not shown or stored. This panel shows persisted evidence and factors.',
  internal_prompt: 'hidden chain thought content must not render',
}

function setupFetch(
  latestInvestigation: Investigation | null,
  latestAssessment: Assessment | null | Record<string, unknown>,
  activeAssessment: Assessment = {
    ...assessment,
    id: 'assessment-new',
    status: 'running',
  },
) {
  return vi.spyOn(globalThis, 'fetch').mockImplementation((input) => {
    const url = requestUrl(input)
    if (url.endsWith('/auth/me'))
      return Promise.resolve(jsonResponse(userResponse))
    if (url.includes('/knowledge/search?'))
      return Promise.resolve(
        jsonResponse({
          query: ticket.title,
          embedding_model: 'local',
          items: [],
        }),
      )
    if (url.endsWith(`/tickets/${ticket.id}/analyses/latest`))
      return Promise.resolve(jsonResponse(analysis))
    if (url.endsWith(`/tickets/${ticket.id}/investigations/latest`))
      return Promise.resolve(jsonResponse(latestInvestigation))
    if (url.endsWith(`/tickets/${ticket.id}/assessments/latest`))
      return Promise.resolve(jsonResponse(latestAssessment))
    if (url.endsWith(`/tickets/${ticket.id}/assessments`))
      return Promise.resolve(
        jsonResponse(
          { assessment_id: 'assessment-new', status: 'queued' },
          202,
        ),
      )
    if (url.endsWith('/assessments/assessment-new'))
      return Promise.resolve(jsonResponse(activeAssessment))
    if (url.endsWith('/assessments/assessment-1/retry'))
      return Promise.resolve(
        jsonResponse(
          { assessment_id: 'assessment-new', status: 'queued' },
          202,
        ),
      )
    if (url.endsWith('/assessments/assessment-1/explanation'))
      return Promise.resolve(jsonResponse(explanation))
    if (url.endsWith(`/tickets/${ticket.id}`))
      return Promise.resolve(jsonResponse(ticket))
    if (url.endsWith(`/tickets/${ticket.id}/events`))
      return Promise.resolve(jsonResponse([]))
    if (url.endsWith('/users')) return Promise.resolve(jsonResponse([]))
    return Promise.resolve(jsonResponse({ status: 'ready' }))
  })
}

function csrfHeader(init: RequestInit | undefined) {
  return new Headers(init?.headers).get('X-CSRF-Token')
}

describe('Root Cause Assessment', () => {
  it('requires a completed investigation before offering generation', async () => {
    setupFetch(null, null)
    renderApp(`/tickets/${ticket.id}`)

    expect(
      await screen.findByRole('heading', {
        name: 'Completed investigation required',
      }),
    ).toBeInTheDocument()
    expect(
      screen.queryByRole('button', { name: 'Generate assessment' }),
    ).not.toBeInTheDocument()
  })

  it('starts with CSRF and polls only while active', async () => {
    const user = userEvent.setup()
    const fetchMock = setupFetch(investigation, null)
    renderApp(`/tickets/${ticket.id}`)

    await user.click(
      await screen.findByRole('button', { name: 'Generate assessment' }),
    )
    expect(
      await screen.findByRole('heading', { name: 'Assessment running' }),
    ).toBeInTheDocument()
    const request = fetchMock.mock.calls.find(
      ([input, init]) =>
        requestUrl(input).endsWith(`/tickets/${ticket.id}/assessments`) &&
        init?.method === 'POST',
    )
    expect(csrfHeader(request?.[1])).toBe('csrf-test-token')
    await waitFor(
      () => {
        const polls = fetchMock.mock.calls.filter(([input]) =>
          requestUrl(input).endsWith('/assessments/assessment-new'),
        )
        expect(polls.length).toBeGreaterThan(1)
      },
      { timeout: 2200 },
    )
  })

  it('orders evidence before inference and presents bounded guidance', async () => {
    setupFetch(investigation, assessment)
    renderApp(`/tickets/${ticket.id}`)

    const heading = await screen.findByRole('heading', {
      name: 'Root Cause Assessment',
    })
    const section = heading.closest('section')
    if (!section) throw new Error('Assessment section was not rendered.')
    expect(await within(section).findByText('STATUS-DAL-7')).toBeInTheDocument()
    expect(within(section).getByText('TEL-DAL-19')).toBeInTheDocument()
    expect(
      within(section).getByText(/Regional service degradation/),
    ).toBeInTheDocument()
    expect(
      within(section).getByText(/Elevated resolver latency/),
    ).toBeInTheDocument()
    expect(
      within(section).getByText('Dallas DNS service degradation'),
    ).toBeInTheDocument()
    expect(within(section).getByText('91%')).toBeInTheDocument()
    expect(
      within(section).getByText(
        'Review Dallas resolver health and failover readiness.',
      ),
    ).toBeInTheDocument()
    expect(
      within(section).getByText('Deterministic demo inference'),
    ).toBeInTheDocument()
    expect(
      within(section).getByText('AI inference - not confirmed'),
    ).toBeInTheDocument()
    expect(
      within(section).getByText('Recommendation - human review required'),
    ).toBeInTheDocument()
    expect(section.textContent?.indexOf('Observed Evidence')).toBeLessThan(
      section.textContent?.indexOf('Probable Root Cause') ?? -1,
    )
  })

  it('uses the server escalation decision and displays its threshold', async () => {
    setupFetch(investigation, {
      ...assessment,
      escalation: {
        required: true,
        threshold: 0.8,
        reason: 'Independent device evidence is unavailable.',
      },
    })
    renderApp(`/tickets/${ticket.id}`)

    expect(
      await screen.findByText(
        'AI confidence is low. Human investigation recommended.',
      ),
    ).toBeInTheDocument()
    expect(screen.getByText('Escalation threshold 80%')).toBeInTheDocument()
    expect(
      screen.getByText('Independent device evidence is unavailable.'),
    ).toBeInTheDocument()
  })

  it('does not infer escalation from a low score', async () => {
    setupFetch(investigation, {
      ...assessment,
      confidence: { ...assessment.confidence, score: 0.42 },
      escalation: {
        required: false,
        threshold: 0.6,
        reason: 'Server policy did not require escalation.',
      },
    })
    renderApp(`/tickets/${ticket.id}`)

    expect(await screen.findByText('42%')).toBeInTheDocument()
    expect(
      screen.queryByText(
        'AI confidence is low. Human investigation recommended.',
      ),
    ).not.toBeInTheDocument()
    expect(
      screen.queryByText('Server policy did not require escalation.'),
    ).not.toBeInTheDocument()
  })

  it('fetches and toggles the safe explanation lazily', async () => {
    const user = userEvent.setup()
    const fetchMock = setupFetch(investigation, assessment)
    renderApp(`/tickets/${ticket.id}`)
    const show = await screen.findByRole('button', { name: 'Show Me Why' })
    expect(
      fetchMock.mock.calls.some(([input]) =>
        requestUrl(input).endsWith('/assessments/assessment-1/explanation'),
      ),
    ).toBe(false)

    await user.click(show)
    expect(
      await screen.findByText('Checked Dallas service health'),
    ).toBeInTheDocument()
    expect(screen.getAllByText('STATUS-DAL-7')).toHaveLength(2)
    expect(screen.getByText('Independent sources agree')).toBeInTheDocument()
    expect(screen.getByText('independent_sources')).toBeInTheDocument()
    expect(screen.getByText('STATUS-DAL-7, TEL-DAL-19')).toBeInTheDocument()
    expect(screen.getByText('+0.31')).toBeInTheDocument()
    expect(screen.getByText('-0.08')).toBeInTheDocument()
    expect(
      screen.getByText(/Hidden chain-of-thought is not shown or stored/),
    ).toBeInTheDocument()
    expect(
      screen.queryByText('hidden chain thought content must not render'),
    ).not.toBeInTheDocument()
    expect(screen.queryByText('internal_key')).not.toBeInTheDocument()
    expect(
      screen.queryByText('do not display nested assessment internals'),
    ).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Close' }))
    expect(
      screen.queryByRole('heading', { name: 'Why this assessment?' }),
    ).not.toBeInTheDocument()
  })

  it('retries failures with CSRF and safely rejects malformed results', async () => {
    const user = userEvent.setup()
    const failed = { ...assessment, status: 'failed' as const }
    const fetchMock = setupFetch(investigation, failed)
    const view = renderApp(`/tickets/${ticket.id}`)
    await user.click(
      await screen.findByRole('button', { name: 'Retry assessment' }),
    )
    const retry = fetchMock.mock.calls.find(([input]) =>
      requestUrl(input).endsWith('/assessments/assessment-1/retry'),
    )
    expect(retry?.[1]?.method).toBe('POST')
    expect(csrfHeader(retry?.[1])).toBe('csrf-test-token')

    view.unmount()
    fetchMock.mockRestore()
    setupFetch(investigation, {
      ...assessment,
      observed_evidence: undefined,
      evidence,
      confidence: 0.91,
      confidence_version: 'old-flat-contract',
      requires_escalation: false,
    })
    renderApp(`/tickets/${ticket.id}`)
    expect(
      await screen.findByText(
        'Assessment data is unavailable because the service returned an invalid response.',
      ),
    ).toBeInTheDocument()
  })
})
