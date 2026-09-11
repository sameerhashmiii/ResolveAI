export interface HealthCheck {
  status: string
  detail?: string
}

export interface HealthReadyResponse {
  status: string
  service?: string
  version?: string
  timestamp?: string
  checks?: Record<string, HealthCheck>
}

export class HealthApiError extends Error {
  constructor(
    message: string,
    public readonly status?: number,
  ) {
    super(message)
    this.name = 'HealthApiError'
  }
}

export async function getHealthReady(
  signal?: AbortSignal,
): Promise<HealthReadyResponse> {
  let response: Response

  try {
    response = await fetch('/api/v1/health/ready', {
      headers: { Accept: 'application/json' },
      signal,
    })
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw error
    }
    throw new HealthApiError('The readiness service could not be reached.')
  }

  if (!response.ok) {
    throw new HealthApiError(
      `The readiness service returned HTTP ${String(response.status)}.`,
      response.status,
    )
  }

  const data: unknown = await response.json()
  if (
    typeof data !== 'object' ||
    data === null ||
    !('status' in data) ||
    typeof data.status !== 'string'
  ) {
    throw new HealthApiError('The readiness response was not valid.')
  }

  return data as HealthReadyResponse
}
