import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'

import {
  createInvestigation,
  getInvestigation,
  getLatestInvestigation,
  retryInvestigation,
} from '../../api/investigations'
import type { Investigation } from '../../api/types'

const isActive = (value: Investigation | null | undefined) =>
  value?.status === 'queued' || value?.status === 'running'

export function useInvestigation(
  ticketId: string,
  csrfToken: string | null,
  enabled: boolean,
) {
  const queryClient = useQueryClient()
  const [activeId, setActiveId] = useState<string | null>(null)
  const latestKey = ['ticket', ticketId, 'investigation', 'latest'] as const
  const latest = useQuery({
    queryKey: latestKey,
    queryFn: ({ signal }) => getLatestInvestigation(ticketId, signal),
    enabled: enabled && Boolean(ticketId),
    refetchInterval: (query) =>
      !activeId && isActive(query.state.data) ? 1000 : false,
  })
  const active = useQuery({
    queryKey: ['investigation', activeId],
    queryFn: ({ signal }) => {
      if (!activeId) throw new Error('No active investigation was selected.')
      return getInvestigation(activeId, signal)
    },
    enabled: Boolean(activeId),
    refetchInterval: (query) => (isActive(query.state.data) ? 1000 : false),
  })

  useEffect(() => {
    if (!active.data || isActive(active.data)) return
    queryClient.setQueryData(
      ['ticket', ticketId, 'investigation', 'latest'],
      active.data,
    )
    setActiveId(null)
    void queryClient.invalidateQueries({
      queryKey: ['ticket', ticketId, 'events'],
    })
  }, [active.data, queryClient, ticketId])

  const accept = (investigationId: string) => {
    setActiveId(investigationId)
    void queryClient.invalidateQueries({ queryKey: latestKey })
  }
  const start = useMutation({
    mutationFn: () => {
      if (!csrfToken)
        throw new Error('Your session is missing a security token.')
      return createInvestigation(ticketId, csrfToken)
    },
    onSuccess: (response) => accept(response.investigation_id),
  })
  const retry = useMutation({
    mutationFn: (investigationId: string) => {
      if (!csrfToken)
        throw new Error('Your session is missing a security token.')
      return retryInvestigation(investigationId, csrfToken)
    },
    onSuccess: (response) => accept(response.investigation_id),
  })

  return {
    investigation: active.data ?? latest.data,
    latest,
    start,
    retry,
  }
}
