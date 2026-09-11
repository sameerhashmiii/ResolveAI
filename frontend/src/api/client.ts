const API_ROOT = '/api/v1'

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status?: number,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

interface RequestOptions extends Omit<RequestInit, 'body'> {
  body?: unknown
  csrfToken?: string | null
}

function safeErrorMessage(status: number, payload: unknown) {
  if (typeof payload === 'object' && payload !== null) {
    const value =
      'detail' in payload
        ? payload.detail
        : 'message' in payload
          ? payload.message
          : undefined
    if (typeof value === 'string' && value.length <= 300) return value
  }

  if (status === 401) return 'Your session has expired. Please sign in again.'
  if (status === 403) return 'You do not have permission to do that.'
  if (status === 404) return 'The requested record could not be found.'
  if (status >= 500) return 'ResolveAI is temporarily unavailable.'
  return 'The request could not be completed.'
}

export async function apiRequest<T>(
  path: string,
  { body, csrfToken, headers, ...options }: RequestOptions = {},
): Promise<T> {
  let response: Response
  const requestHeaders = new Headers(headers)
  requestHeaders.set('Accept', 'application/json')
  if (body !== undefined) requestHeaders.set('Content-Type', 'application/json')
  if (csrfToken) requestHeaders.set('X-CSRF-Token', csrfToken)

  try {
    response = await fetch(`${API_ROOT}${path}`, {
      ...options,
      credentials: 'include',
      headers: requestHeaders,
      body: body === undefined ? undefined : JSON.stringify(body),
    })
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError')
      throw error
    throw new ApiError('ResolveAI could not be reached. Check your connection.')
  }

  if (!response.ok) {
    let payload: unknown
    try {
      const data: unknown = await response.json()
      payload = data
    } catch {
      payload = undefined
    }
    throw new ApiError(
      safeErrorMessage(response.status, payload),
      response.status,
    )
  }

  if (response.status === 204) return undefined as T
  try {
    const data: unknown = await response.json()
    return data as T
  } catch {
    throw new ApiError(
      'ResolveAI returned an invalid response.',
      response.status,
    )
  }
}
