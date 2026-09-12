import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'

import {
  createAnalysis,
  getAnalysis,
  getLatestAnalysis,
  retryAnalysis,
} from '../../api/analyses'
import type { Analysis } from '../../api/types'

const isActive = (analysis: Analysis | null | undefined) =>
  analysis?.status === 'queued' || analysis?.status === 'running'

export function useTicketTriage(ticketId: string, csrfToken: string | null) {
  const queryClient = useQueryClient()
  const [activeAnalysisId, setActiveAnalysisId] = useState<string | null>(null)
  const latestKey = ['ticket', ticketId, 'analysis', 'latest'] as const
  const latest = useQuery({
    queryKey: latestKey,
    queryFn: ({ signal }) => getLatestAnalysis(ticketId, signal),
    enabled: Boolean(ticketId),
    refetchInterval: (query) =>
      !activeAnalysisId && isActive(query.state.data) ? 1000 : false,
  })
  const active = useQuery({
    queryKey: ['analysis', activeAnalysisId],
    queryFn: ({ signal }) => {
      if (!activeAnalysisId) throw new Error('No active analysis was selected.')
      return getAnalysis(activeAnalysisId, signal)
    },
    enabled: Boolean(activeAnalysisId),
    refetchInterval: (query) => (isActive(query.state.data) ? 1000 : false),
  })

  useEffect(() => {
    if (!active.data || isActive(active.data)) return
    queryClient.setQueryData(
      ['ticket', ticketId, 'analysis', 'latest'],
      active.data,
    )
    setActiveAnalysisId(null)
    void Promise.all([
      queryClient.invalidateQueries({ queryKey: ['ticket', ticketId] }),
      queryClient.invalidateQueries({
        queryKey: ['ticket', ticketId, 'events'],
      }),
      queryClient.invalidateQueries({ queryKey: ['tickets'] }),
      queryClient.invalidateQueries({ queryKey: ['dashboard'] }),
    ])
  }, [active.data, queryClient, ticketId])

  const settleAcceptedAnalysis = (analysisId: string) => {
    setActiveAnalysisId(analysisId)
    void queryClient.invalidateQueries({ queryKey: latestKey })
  }
  const analyze = useMutation({
    mutationFn: () => {
      if (!csrfToken)
        throw new Error('Your session is missing a security token.')
      return createAnalysis(ticketId, csrfToken)
    },
    onSuccess: (response) => settleAcceptedAnalysis(response.analysis_id),
  })
  const retry = useMutation({
    mutationFn: (analysisId: string) => {
      if (!csrfToken)
        throw new Error('Your session is missing a security token.')
      return retryAnalysis(analysisId, csrfToken)
    },
    onSuccess: (response) => settleAcceptedAnalysis(response.analysis_id),
  })

  const analysis = active.data ?? latest.data

  return { analysis, latest, analyze, retry }
}
