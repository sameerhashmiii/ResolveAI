import { useQuery } from '@tanstack/react-query'

import { getHealthReady } from '../api/health'

export function PlatformHealth() {
  const health = useQuery({
    queryKey: ['health', 'ready'],
    queryFn: ({ signal }) => getHealthReady(signal),
    refetchInterval: 30_000,
  })
  const ready = health.data?.status.toLowerCase() === 'ready'
  const label = health.isPending
    ? 'Checking'
    : ready
      ? 'Operational'
      : 'Degraded'

  return (
    <span
      className={`platform-health platform-health--${ready ? 'ready' : 'other'}`}
      role="status"
      aria-label={`Platform health: ${label}`}
    >
      <span aria-hidden="true" />
      {label}
    </span>
  )
}
