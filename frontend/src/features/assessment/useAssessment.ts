import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'

import {
  createAssessment,
  getAssessment,
  getLatestAssessment,
  retryAssessment,
} from '../../api/assessments'

function isActive(value: unknown) {
  if (typeof value !== 'object' || value === null || !('status' in value))
    return false
  return value.status === 'queued' || value.status === 'running'
}

export function useAssessment(
  ticketId: string,
  csrfToken: string | null,
  enabled: boolean,
) {
  const queryClient = useQueryClient()
  const [activeId, setActiveId] = useState<string | null>(null)
  const latestKey = ['ticket', ticketId, 'assessment', 'latest'] as const
  const latest = useQuery({
    queryKey: latestKey,
    queryFn: ({ signal }) => getLatestAssessment(ticketId, signal),
    enabled: enabled && Boolean(ticketId),
    refetchInterval: (query) =>
      !activeId && isActive(query.state.data) ? 1000 : false,
  })
  const active = useQuery({
    queryKey: ['assessment', activeId],
    queryFn: ({ signal }) => {
      if (!activeId) throw new Error('No active assessment was selected.')
      return getAssessment(activeId, signal)
    },
    enabled: Boolean(activeId),
    refetchInterval: (query) => (isActive(query.state.data) ? 1000 : false),
  })

  useEffect(() => {
    if (active.data === undefined || isActive(active.data)) return
    queryClient.setQueryData(
      ['ticket', ticketId, 'assessment', 'latest'],
      active.data,
    )
    setActiveId(null)
  }, [active.data, queryClient, ticketId])

  const accept = (assessmentId: string) => {
    setActiveId(assessmentId)
    void queryClient.invalidateQueries({ queryKey: latestKey })
  }
  const start = useMutation({
    mutationFn: () => {
      if (!csrfToken)
        throw new Error('Your session is missing a security token.')
      return createAssessment(ticketId, csrfToken)
    },
    onSuccess: (response) => accept(response.assessment_id),
  })
  const retry = useMutation({
    mutationFn: (assessmentId: string) => {
      if (!csrfToken)
        throw new Error('Your session is missing a security token.')
      return retryAssessment(assessmentId, csrfToken)
    },
    onSuccess: (response) => accept(response.assessment_id),
  })

  return { assessment: active.data ?? latest.data, latest, start, retry }
}
