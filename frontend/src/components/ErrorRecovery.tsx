import { Component, type ReactNode } from 'react'
import { useRouteError } from 'react-router-dom'

export function ErrorRecovery() {
  return (
    <main className="error-recovery">
      <div className="content-card error-recovery__card" role="alert">
        <p className="section-label">Workspace recovery</p>
        <h1>Something went wrong.</h1>
        <p>
          ResolveAI could not display this page. Your data has not been changed.
        </p>
        <div className="form-actions">
          <a className="button button--primary" href="/">
            Return home
          </a>
          <button
            className="button button--outline"
            type="button"
            onClick={() => window.location.reload()}
          >
            Reload page
          </button>
        </div>
      </div>
    </main>
  )
}

export function RouterErrorRecovery() {
  useRouteError()
  return <ErrorRecovery />
}

interface ErrorBoundaryState {
  failed: boolean
}

export class ErrorBoundary extends Component<
  { children: ReactNode },
  ErrorBoundaryState
> {
  state: ErrorBoundaryState = { failed: false }

  static getDerivedStateFromError(): ErrorBoundaryState {
    return { failed: true }
  }

  componentDidCatch() {
    console.error('ResolveAI rendering failed')
  }

  render() {
    return this.state.failed ? <ErrorRecovery /> : this.props.children
  }
}
