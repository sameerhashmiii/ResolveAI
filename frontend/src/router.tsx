import {
  Navigate,
  createBrowserRouter,
  useLocation,
  type RouteObject,
} from 'react-router-dom'

import { useAuth } from './auth/AuthContext'
import { AppShell } from './components/AppShell'
import { RouterErrorRecovery } from './components/ErrorRecovery'
import { AdminObservabilityPage } from './pages/AdminObservabilityPage'
import { CreateTicketPage } from './pages/CreateTicketPage'
import { DashboardPage } from './pages/DashboardPage'
import { LoginPage } from './pages/LoginPage'
import { TicketDetailPage } from './pages/TicketDetailPage'
import { TicketsPage } from './pages/TicketsPage'

export function ProtectedRoute() {
  const { user, isLoading } = useAuth()
  const location = useLocation()
  if (isLoading)
    return (
      <div className="auth-loading" role="status">
        Preparing your workspace...
      </div>
    )
  if (!user)
    return (
      <Navigate
        to="/login"
        replace
        state={{ from: `${location.pathname}${location.search}` }}
      />
    )
  return <AppShell />
}

export function AdministratorRoute() {
  const { user } = useAuth()
  return user?.role === 'administrator' ? (
    <AdminObservabilityPage />
  ) : (
    <Navigate to="/" replace />
  )
}

export const routes: RouteObject[] = [
  {
    path: '/login',
    element: <LoginPage />,
    errorElement: <RouterErrorRecovery />,
  },
  {
    path: '/',
    element: <ProtectedRoute />,
    errorElement: <RouterErrorRecovery />,
    children: [
      { index: true, element: <DashboardPage /> },
      { path: 'tickets', element: <TicketsPage /> },
      { path: 'tickets/new', element: <CreateTicketPage /> },
      { path: 'tickets/:id', element: <TicketDetailPage /> },
      { path: 'admin/observability', element: <AdministratorRoute /> },
    ],
  },
  { path: '*', element: <Navigate to="/" replace /> },
]

export const router = createBrowserRouter(routes)
