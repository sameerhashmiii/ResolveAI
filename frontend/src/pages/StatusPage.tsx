import { useEffect } from 'react'
import { Link } from 'react-router-dom'

export function AccessDeniedPage() {
  useEffect(() => {
    document.title = 'Access denied | ResolveAI'
  }, [])
  return (
    <div className="page status-page">
      <p className="eyebrow">Access denied</p>
      <h1>This view requires administrator access.</h1>
      <p>
        Your session is valid, but your role does not include service health and
        full observability.
      </p>
      <Link className="button button--primary" to="/workspace">
        Return to workspace
      </Link>
    </div>
  )
}

export function NotFoundPage() {
  useEffect(() => {
    document.title = 'Page not found | ResolveAI'
  }, [])
  return (
    <main id="main-content" className="status-page status-page--public">
      <p className="eyebrow">404 / Not found</p>
      <h1>This page is not in the dossier.</h1>
      <p>Check the address or return to the public overview.</p>
      <Link className="button button--primary" to="/">
        Return home
      </Link>
    </main>
  )
}
