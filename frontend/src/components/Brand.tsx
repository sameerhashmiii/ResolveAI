import { Link } from 'react-router-dom'

export function Brand({ publicLink = false }: { publicLink?: boolean }) {
  return (
    <Link className="brand" to={publicLink ? '/login' : '/'}>
      <span className="brand-mark" aria-hidden="true">
        R
      </span>
      <span>
        <strong>ResolveAI</strong>
        <small>Service Intelligence</small>
      </span>
    </Link>
  )
}
