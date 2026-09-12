import { Link } from 'react-router-dom'

export function Brand({ publicLink = false }: { publicLink?: boolean }) {
  return (
    <Link className="brand" to={publicLink ? '/' : '/workspace'}>
      <span className="brand-mark" aria-hidden="true">
        R
      </span>
      <span>
        <strong>ResolveAI</strong>
        <small>Evidence-led support copilot</small>
      </span>
    </Link>
  )
}
