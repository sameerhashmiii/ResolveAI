import { useEffect, useRef, useState } from 'react'
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'

import { useAuth } from '../auth/AuthContext'
import { Brand } from './Brand'
import { PlatformHealth } from './PlatformHealth'

const mobileQuery = '(max-width: 920px)'

export function AppShell() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [menuOpen, setMenuOpen] = useState(false)
  const [isMobile, setIsMobile] = useState(
    () => window.matchMedia(mobileQuery).matches,
  )
  const menuButtonRef = useRef<HTMLButtonElement>(null)
  const wasOpen = useRef(false)

  useEffect(() => {
    const media = window.matchMedia(mobileQuery)
    const update = () => setIsMobile(media.matches)
    update()
    media.addEventListener('change', update)
    return () => media.removeEventListener('change', update)
  }, [])

  useEffect(() => {
    setMenuOpen(false)
  }, [location.pathname])

  useEffect(() => {
    if (wasOpen.current && !menuOpen) menuButtonRef.current?.focus()
    wasOpen.current = menuOpen
  }, [menuOpen])

  useEffect(() => {
    if (!menuOpen || !isMobile) return
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setMenuOpen(false)
    }
    document.addEventListener('keydown', closeOnEscape)
    return () => document.removeEventListener('keydown', closeOnEscape)
  }, [isMobile, menuOpen])

  const signOut = async () => {
    try {
      await logout()
    } finally {
      await navigate('/login', { replace: true })
    }
  }

  return (
    <div className="product-shell">
      <header className="mobile-header">
        <Brand />
        <button
          ref={menuButtonRef}
          className="menu-button"
          type="button"
          aria-expanded={menuOpen}
          aria-controls="primary-navigation"
          onClick={() => setMenuOpen((open) => !open)}
        >
          Menu
        </button>
      </header>
      {isMobile && menuOpen && (
        <button
          className="menu-backdrop"
          type="button"
          aria-label="Close navigation menu"
          onClick={() => setMenuOpen(false)}
        />
      )}
      <aside
        className={`sidebar ${menuOpen ? 'sidebar--open' : ''}`}
        aria-hidden={isMobile && !menuOpen ? true : undefined}
        inert={isMobile && !menuOpen ? true : undefined}
      >
        <Brand />
        <nav id="primary-navigation" aria-label="Primary navigation">
          <NavLink to="/" end onClick={() => setMenuOpen(false)}>
            <span aria-hidden="true">01</span> Overview
          </NavLink>
          <NavLink to="/tickets" onClick={() => setMenuOpen(false)}>
            <span aria-hidden="true">02</span> Tickets
          </NavLink>
          <NavLink to="/tickets/new" onClick={() => setMenuOpen(false)}>
            <span aria-hidden="true">03</span> New request
          </NavLink>
          {user?.role === 'administrator' && (
            <NavLink
              to="/admin/observability"
              onClick={() => setMenuOpen(false)}
            >
              <span aria-hidden="true">04</span> Observability
            </NavLink>
          )}
        </nav>
        <div className="sidebar-footer">
          <PlatformHealth />
          <div className="user-card">
            <span className="user-initial" aria-hidden="true">
              {user?.display_name.charAt(0).toUpperCase()}
            </span>
            <span>
              <strong>{user?.display_name}</strong>
              <small>{user?.role.replaceAll('_', ' ')}</small>
            </span>
          </div>
          <button
            className="text-button"
            type="button"
            onClick={() => void signOut()}
          >
            Sign out
          </button>
        </div>
      </aside>
      <main className="product-main">
        {user?.is_demo && (
          <aside
            className="demo-environment"
            aria-label="Demo environment notice"
          >
            <strong>Demo environment</strong>
            <span>
              All users, tickets, applications, incidents, telemetry, logs, and
              knowledge articles are synthetic.
            </span>
          </aside>
        )}
        <Outlet />
      </main>
    </div>
  )
}
