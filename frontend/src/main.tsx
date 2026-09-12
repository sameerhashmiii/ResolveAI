import { QueryClientProvider } from '@tanstack/react-query'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { RouterProvider } from 'react-router-dom'

import { createQueryClient } from './queryClient'
import { router } from './router'
import { AuthProvider } from './auth/AuthContext'
import { ErrorBoundary } from './components/ErrorRecovery'
import './styles.css'

const queryClient = createQueryClient()
const rootElement = document.getElementById('root')

if (!rootElement) {
  throw new Error('ResolveAI could not find its application root.')
}

createRoot(rootElement).render(
  <StrictMode>
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <RouterProvider router={router} />
        </AuthProvider>
      </QueryClientProvider>
    </ErrorBoundary>
  </StrictMode>,
)
