import { apiRequest } from './client'
import type { AuthResponse } from './types'

export const getCurrentUser = (signal?: AbortSignal) =>
  apiRequest<AuthResponse>('/auth/me', { signal })

export const login = (email: string, password: string) =>
  apiRequest<AuthResponse>('/auth/login', {
    method: 'POST',
    body: { email, password },
  })

export const demoLogin = () =>
  apiRequest<AuthResponse>('/auth/demo', { method: 'POST' })

export const logout = (csrfToken: string) =>
  apiRequest<undefined>('/auth/logout', {
    method: 'POST',
    csrfToken,
  })
