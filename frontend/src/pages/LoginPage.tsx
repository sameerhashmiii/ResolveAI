import { useState, type FormEvent } from 'react'
import { Navigate, useLocation, useNavigate } from 'react-router-dom'

import { ApiError } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import { Brand } from '../components/Brand'

export function LoginPage() {
  const { user, isLoading, login, demoLogin } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState<'login' | 'demo' | null>(null)

  if (isLoading) {
    return (
      <div className="auth-loading" role="status">
        Checking your session...
      </div>
    )
  }
  if (user) return <Navigate to="/" replace />

  const routeState: unknown = location.state
  const destination =
    typeof routeState === 'object' &&
    routeState !== null &&
    'from' in routeState &&
    typeof routeState.from === 'string'
      ? routeState.from
      : '/'

  const run = async (kind: 'login' | 'demo', action: () => Promise<void>) => {
    setError('')
    setSubmitting(kind)
    try {
      await action()
      await navigate(destination, { replace: true })
    } catch (requestError) {
      setError(
        requestError instanceof ApiError
          ? requestError.message
          : 'Sign in could not be completed.',
      )
    } finally {
      setSubmitting(null)
    }
  }

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const data = new FormData(event.currentTarget)
    const email = data.get('email')
    const password = data.get('password')
    void run('login', () =>
      login(
        typeof email === 'string' ? email : '',
        typeof password === 'string' ? password : '',
      ),
    )
  }

  return (
    <main className="login-page">
      <section className="login-story" aria-labelledby="login-heading">
        <Brand publicLink />
        <div className="story-copy">
          <p className="eyebrow">Service operations, made legible</p>
          <h1 id="login-heading">Resolve the work behind every request.</h1>
          <p>
            ResolveAI gives support teams a shared operating record for intake,
            ownership, and resolution, without losing the human context behind
            the ticket.
          </p>
        </div>
        <div className="proof-strip" aria-label="Product capabilities">
          <span>Structured intake</span>
          <span>Visible ownership</span>
          <span>Auditable activity</span>
        </div>
      </section>

      <section className="login-panel" aria-labelledby="sign-in-title">
        <div className="login-card">
          <p className="section-label">Workspace access</p>
          <h2 id="sign-in-title">Sign in to ResolveAI</h2>
          <p className="muted">
            Continue to your service operations workspace.
          </p>
          <form onSubmit={submit}>
            <label htmlFor="email">Work email</label>
            <input
              id="email"
              name="email"
              type="email"
              autoComplete="email"
              required
            />
            <label htmlFor="password">Password</label>
            <input
              id="password"
              name="password"
              type="password"
              autoComplete="current-password"
              required
            />
            {error && (
              <p className="form-error" role="alert">
                {error}
              </p>
            )}
            <button
              className="button button--primary button--wide"
              disabled={submitting !== null}
            >
              {submitting === 'login' ? 'Signing in...' : 'Sign in'}
            </button>
          </form>
          <div className="or-divider">
            <span>or explore the product</span>
          </div>
          <button
            className="button button--outline button--wide"
            type="button"
            disabled={submitting !== null}
            onClick={() => void run('demo', demoLogin)}
          >
            {submitting === 'demo' ? 'Preparing workspace...' : 'Try Demo'}
          </button>
          <p className="demo-note">
            Uses synthetic sample tickets in an isolated demo workspace. No
            customer or employee data is included.
          </p>
        </div>
      </section>
    </main>
  )
}
