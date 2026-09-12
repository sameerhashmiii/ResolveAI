import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'

import { getLatestAssessment } from '../../api/assessments'
import {
  approveResponse,
  decideRecommendation,
  escalateTicket,
  generateResponse,
  getLatestRecommendation,
  getLatestResponse,
  rejectResponse,
  resolveTicket,
  saveResponse,
} from '../../api/resolution'
import type { TicketDetail } from '../../api/types'
import { parseAssessment } from '../assessment/parsing'
import { RecommendationPanel } from './RecommendationPanel'
import { ResponsePanel } from './ResponsePanel'
import { TerminalActions } from './TerminalActions'

interface Props {
  ticket: TicketDetail
  csrfToken: string | null
  userRole: string | undefined
}

export function HumanDecisionResolution({
  ticket,
  csrfToken,
  userRole,
}: Props) {
  const queryClient = useQueryClient()
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const assessmentQuery = useQuery({
    queryKey: ['ticket', ticket.id, 'assessment', 'latest'],
    queryFn: ({ signal }) => getLatestAssessment(ticket.id, signal),
  })
  const assessment = parseAssessment(assessmentQuery.data)
  const prerequisiteMet = assessment?.status === 'completed'
  const recommendationQuery = useQuery({
    queryKey: ['ticket', ticket.id, 'recommendation', 'latest'],
    queryFn: ({ signal }) => getLatestRecommendation(ticket.id, signal),
    enabled: prerequisiteMet,
  })
  const responseQuery = useQuery({
    queryKey: ['ticket', ticket.id, 'response', 'latest'],
    queryFn: ({ signal }) => getLatestResponse(ticket.id, signal),
    enabled: prerequisiteMet,
  })
  const terminal = ticket.status === 'resolved' || ticket.status === 'escalated'
  const requireToken = () => {
    if (!csrfToken) throw new Error('Your session is missing a security token.')
    return csrfToken
  }
  const refresh = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['ticket', ticket.id] }),
      queryClient.invalidateQueries({ queryKey: ['tickets'] }),
      queryClient.invalidateQueries({ queryKey: ['dashboard'] }),
      queryClient.invalidateQueries({
        queryKey: ['ticket', ticket.id, 'recommendation', 'latest'],
      }),
      queryClient.invalidateQueries({
        queryKey: ['ticket', ticket.id, 'response', 'latest'],
      }),
    ])
  }
  const success = (text: string) => async () => {
    setError(null)
    setMessage(text)
    await refresh()
  }
  const failure = (reason: Error) => {
    setMessage(null)
    setError(reason.message)
  }
  const decision = useMutation({
    mutationFn: (input: Parameters<typeof decideRecommendation>[1]) => {
      const recommendation = recommendationQuery.data
      if (!recommendation) throw new Error('No recommendation is available.')
      return decideRecommendation(recommendation.id, input, requireToken())
    },
    onSuccess: success('Recommendation decision recorded.'),
    onError: failure,
  })
  const generate = useMutation({
    mutationFn: () => generateResponse(ticket.id, requireToken()),
    onSuccess: success('Customer response draft generated.'),
    onError: failure,
  })
  const save = useMutation({
    mutationFn: (body: string) => {
      if (!responseQuery.data)
        throw new Error('No response draft is available.')
      return saveResponse(responseQuery.data.id, body, requireToken())
    },
    onSuccess: success('Response draft saved.'),
    onError: failure,
  })
  const approve = useMutation({
    mutationFn: async (body: string) => {
      if (!responseQuery.data)
        throw new Error('No response draft is available.')
      if (body.trim() !== responseQuery.data.draft_body) {
        await saveResponse(responseQuery.data.id, body, requireToken())
      }
      return approveResponse(responseQuery.data.id, requireToken())
    },
    onSuccess: success('Response approved. It has not been sent.'),
    onError: failure,
  })
  const reject = useMutation({
    mutationFn: (reason: string) => {
      if (!responseQuery.data)
        throw new Error('No response draft is available.')
      return rejectResponse(responseQuery.data.id, reason, requireToken())
    },
    onSuccess: success('Response rejected.'),
    onError: failure,
  })
  const resolve = useMutation({
    mutationFn: (summary: string) => {
      if (responseQuery.data?.status !== 'approved')
        throw new Error('An approved response is required.')
      return resolveTicket(
        ticket.id,
        responseQuery.data.id,
        summary,
        requireToken(),
      )
    },
    onSuccess: success('Ticket resolved.'),
    onError: failure,
  })
  const escalate = useMutation({
    mutationFn: ({
      destination,
      reason,
    }: {
      destination: string
      reason: string
    }) => escalateTicket(ticket.id, destination, reason, requireToken()),
    onSuccess: success('Ticket escalated.'),
    onError: failure,
  })
  const pending =
    decision.isPending ||
    generate.isPending ||
    save.isPending ||
    approve.isPending ||
    reject.isPending ||
    resolve.isPending ||
    escalate.isPending
  const dataError =
    assessmentQuery.error ?? recommendationQuery.error ?? responseQuery.error

  return (
    <section
      className="content-card resolution-card"
      aria-labelledby="resolution-title"
    >
      <div className="section-heading resolution-heading">
        <div>
          <p className="section-label">Controlled human workflow</p>
          <h2 id="resolution-title">Human Decision &amp; Resolution</h2>
        </div>
      </div>
      {assessmentQuery.isPending && (
        <div className="resolution-state" role="status">
          Checking assessment status...
        </div>
      )}
      {!assessmentQuery.isPending && assessmentQuery.error && (
        <div className="resolution-state resolution-state--error" role="alert">
          Resolution prerequisites are unavailable.{' '}
          {assessmentQuery.error.message}
        </div>
      )}
      {!assessmentQuery.isPending && !dataError && !prerequisiteMet && (
        <div className="resolution-state">
          <h3>Completed assessment required</h3>
          <p>
            Complete Root Cause Assessment before reviewing recommendations or
            taking terminal actions.
          </p>
        </div>
      )}
      {prerequisiteMet &&
        (recommendationQuery.isPending || responseQuery.isPending) && (
          <div className="resolution-state" role="status">
            Loading recommendation and response...
          </div>
        )}
      {prerequisiteMet && dataError && (
        <div className="resolution-state resolution-state--error" role="alert">
          Recommendation or response data is unavailable. {dataError.message}
        </div>
      )}
      {prerequisiteMet &&
        !dataError &&
        !recommendationQuery.isPending &&
        !responseQuery.isPending && (
          <div className="resolution-body">
            {message && (
              <p className="success-message" role="status">
                {message}
              </p>
            )}
            {error && (
              <p className="form-error" role="alert">
                {error}
              </p>
            )}
            <RecommendationPanel
              recommendation={recommendationQuery.data ?? null}
              isManager={userRole === 'manager' || userRole === 'administrator'}
              disabled={terminal}
              pending={pending}
              onDecision={(input) => decision.mutate(input)}
            />
            <ResponsePanel
              response={responseQuery.data ?? null}
              canGenerate={
                recommendationQuery.data?.status === 'approved' ||
                recommendationQuery.data?.status === 'modified'
              }
              disabled={terminal}
              pending={pending}
              onGenerate={() => generate.mutate()}
              onSave={(body) => save.mutate(body)}
              onApprove={(body) => approve.mutate(body)}
              onReject={(reason) => reject.mutate(reason)}
            />
            <TerminalActions
              ticket={ticket}
              response={responseQuery.data ?? null}
              pending={pending}
              onResolve={(summary) => resolve.mutate(summary)}
              onEscalate={(destination, reason) =>
                escalate.mutate({ destination, reason })
              }
            />
          </div>
        )}
    </section>
  )
}
