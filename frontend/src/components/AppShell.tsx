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
  const sidebarRef = useRef<HTMLElement>(null)
  const wasOpen = useRef(false)
  const initialRoute = useRef(true)
  const menuOpenRef = useRef(menuOpen)
  menuOpenRef.current = menuOpen

  useEffect(() => {
    const media = window.matchMedia(mobileQuery)
    const update = () => setIsMobile(media.matches)
    update()
    media.addEventListener('change', update)
    return () => media.removeEventListener('change', update)
  }, [])

  useEffect(() => {
    setMenuOpen(false)
    const titles: Record<string, string> = {
      '/workspace': 'Workspace',
      '/tickets': 'Tickets',
      '/tickets/new': 'Create request',
      '/analytics': 'Evaluation',
      '/admin/observability': 'Observability',
    }
    const section =
      titles[location.pathname] ??
      (location.pathname.startsWith('/tickets/') ? 'Ticket' : 'ResolveAI')
    document.title = `${section} | ResolveAI`
    if (initialRoute.current) {
      initialRoute.current = false
    } else if (!menuOpenRef.current) {
      window.requestAnimationFrame(() => {
        const heading = document.querySelector<HTMLElement>('#main-content h1')
        if (heading) {
          heading.tabIndex = -1
          heading.focus()
        }
      })
    }
  }, [location.pathname])

  useEffect(() => {
    if (wasOpen.current && !menuOpen) menuButtonRef.current?.focus()
    wasOpen.current = menuOpen
  }, [menuOpen])

  useEffect(() => {
    if (!menuOpen || !isMobile) return
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    const focusable = () =>
      Array.from(
        sidebarRef.current?.querySelectorAll<HTMLElement>(
          'a[href], button:not([disabled]), input:not([disabled])',
        ) ?? [],
      )
    sidebarRef.current?.querySelector<HTMLElement>('nav a[href]')?.focus()
    const handleKeyboard = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setMenuOpen(false)
        return
      }
      if (event.key !== 'Tab') return
      const items = focusable()
      if (!items.length) return
      const first = items.at(0)
      const last = items.at(-1)
      if (!first || !last) return
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault()
        last.focus()
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault()
        first.focus()
      }
    }
    document.addEventListener('keydown', handleKeyboard)
    return () => {
      document.body.style.overflow = previousOverflow
      document.removeEventListener('keydown', handleKeyboard)
    }
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
      <a className="skip-link" href="#main-content">
        Skip to main content
      </a>
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
        ref={sidebarRef}
        className={`sidebar ${menuOpen ? 'sidebar--open' : ''}`}
        aria-hidden={isMobile && !menuOpen ? true : undefined}
        inert={isMobile && !menuOpen ? true : undefined}
      >
        <Brand />
        <nav id="primary-navigation" aria-label="Primary navigation">
          <NavLink to="/workspace" onClick={() => setMenuOpen(false)}>
            <span aria-hidden="true">01</span> Overview
          </NavLink>
          <NavLink to="/tickets" onClick={() => setMenuOpen(false)}>
            <span aria-hidden="true">02</span> Tickets
          </NavLink>
          <NavLink to="/tickets/new" onClick={() => setMenuOpen(false)}>
            <span aria-hidden="true">03</span> New request
          </NavLink>
          <NavLink to="/analytics" onClick={() => setMenuOpen(false)}>
            <span aria-hidden="true">04</span> Evaluation
          </NavLink>
          {user?.role === 'administrator' && (
            <NavLink
              to="/admin/observability"
              onClick={() => setMenuOpen(false)}
            >
              <span aria-hidden="true">05</span> Observability
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
      <main className="product-main" id="main-content">
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
