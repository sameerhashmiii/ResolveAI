import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'

import { AppShell } from './AppShell'

const auth = vi.hoisted(
  (): {
    user: { display_name: string; role: string; is_demo: boolean }
    logout: ReturnType<typeof vi.fn>
  } => ({
    user: {
      display_name: 'Alex Morgan',
      role: 'support_analyst',
      is_demo: false,
    },
    logout: vi.fn(),
  }),
)

vi.mock('../auth/AuthContext', () => ({ useAuth: () => auth }))
vi.mock('./PlatformHealth', () => ({
  PlatformHealth: () => <span>Platform ready</span>,
}))

function setMobile(matches: boolean) {
  const listeners = new Set<() => void>()
  vi.stubGlobal(
    'matchMedia',
    vi.fn().mockReturnValue({
      matches,
      media: '(max-width: 920px)',
      onchange: null,
      addEventListener: (_event: string, listener: () => void) =>
        listeners.add(listener),
      removeEventListener: (_event: string, listener: () => void) =>
        listeners.delete(listener),
      dispatchEvent: () => true,
    }),
  )
}

function renderShell() {
  return render(
    <MemoryRouter initialEntries={['/workspace']}>
      <Routes>
        <Route element={<AppShell />}>
          <Route path="workspace" element={<h1>Overview page</h1>} />
          <Route path="tickets" element={<h1>Tickets page</h1>} />
        </Route>
      </Routes>
    </MemoryRouter>,
  )
}

describe('AppShell mobile navigation', () => {
  afterEach(() => {
    auth.user.role = 'support_analyst'
    vi.unstubAllGlobals()
  })

  it('hides the closed mobile drawer and closes it with Escape', async () => {
    setMobile(true)
    const user = userEvent.setup()
    renderShell()
    const menu = screen.getByRole('button', { name: 'Menu' })
    const sidebar = document.querySelector('.sidebar')

    expect(sidebar).toHaveAttribute('aria-hidden', 'true')
    expect(sidebar).toHaveAttribute('inert')
    await user.click(menu)
    expect(screen.getByRole('link', { name: /Overview/ })).toHaveFocus()
    expect(document.body).toHaveStyle({ overflow: 'hidden' })
    expect(menu).toHaveAttribute('aria-expanded', 'true')
    expect(sidebar).not.toHaveAttribute('aria-hidden')
    expect(
      screen.getByRole('button', { name: 'Close navigation menu' }),
    ).toBeInTheDocument()

    await user.keyboard('{Escape}')
    expect(menu).toHaveAttribute('aria-expanded', 'false')
    expect(menu).toHaveFocus()
    expect(document.body).not.toHaveStyle({ overflow: 'hidden' })
  })

  it('closes on navigation and moves focus to the new page heading', async () => {
    setMobile(true)
    const user = userEvent.setup()
    renderShell()
    const menu = screen.getByRole('button', { name: 'Menu' })

    await user.click(menu)
    await user.click(screen.getByRole('link', { name: /Tickets/ }))

    const heading = await screen.findByRole('heading', { name: 'Tickets page' })
    await waitFor(() => expect(heading).toHaveFocus())
    expect(menu).toHaveAttribute('aria-expanded', 'false')
  })

  it('keeps desktop navigation available and shows admin navigation', () => {
    setMobile(false)
    auth.user.role = 'administrator'
    renderShell()

    const sidebar = document.querySelector('.sidebar')
    expect(sidebar).not.toHaveAttribute('aria-hidden')
    expect(sidebar).not.toHaveAttribute('inert')
    expect(
      screen.getByRole('link', { name: /Observability/ }),
    ).toBeInTheDocument()
  })
})
