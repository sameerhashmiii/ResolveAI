import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render } from '@testing-library/react'
import { MemoryRouter, useRoutes } from 'react-router-dom'

import { AuthProvider } from '../auth/AuthContext'
import { routes } from '../router'

function TestRoutes() {
  return useRoutes(routes)
}

export function renderApp(path: string) {
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: Infinity },
      mutations: { retry: false },
    },
  })

  return render(
    <QueryClientProvider client={client}>
      <AuthProvider>
        <MemoryRouter initialEntries={[path]}>
          <TestRoutes />
        </MemoryRouter>
      </AuthProvider>
    </QueryClientProvider>,
  )
}

export const userResponse = {
  user: {
    id: 'user-1',
    email: 'alex@example.com',
    display_name: 'Alex Morgan',
    role: 'support_analyst',
    is_demo: true,
  },
  csrf_token: 'csrf-test-token',
}

export function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

export function requestUrl(input: RequestInfo | URL) {
  if (typeof input === 'string') return input
  return input instanceof URL ? input.href : input.url
}
