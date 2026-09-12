import { render, screen } from '@testing-library/react'
import type { ReactNode } from 'react'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'

import {
  ErrorBoundary,
  ErrorRecovery,
  RouterErrorRecovery,
} from './ErrorRecovery'

function BrokenPage(): ReactNode {
  throw new Error('sensitive exception detail')
}

describe('error recovery', () => {
  beforeEach(() => {
    vi.spyOn(console, 'error').mockImplementation(() => undefined)
  })

  afterEach(() => vi.restoreAllMocks())

  it('shows safe recovery actions from the top-level boundary', () => {
    render(
      <ErrorBoundary>
        <BrokenPage />
      </ErrorBoundary>,
    )

    expect(
      screen.getByRole('heading', { name: 'Something went wrong.' }),
    ).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Return home' })).toHaveAttribute(
      'href',
      '/',
    )
    expect(
      screen.getByRole('button', { name: 'Reload page' }),
    ).toBeInTheDocument()
    expect(
      screen.queryByText(/sensitive exception detail/i),
    ).not.toBeInTheDocument()
  })

  it('uses the same safe page for router errors', async () => {
    const router = createMemoryRouter([
      {
        path: '/',
        element: <BrokenPage />,
        errorElement: <RouterErrorRecovery />,
      },
    ])
    render(<RouterProvider router={router} />)

    expect(
      await screen.findByRole('heading', { name: 'Something went wrong.' }),
    ).toBeInTheDocument()
    expect(
      screen.queryByText(/sensitive exception detail/i),
    ).not.toBeInTheDocument()
  })

  it('renders recovery content independently of router context', () => {
    render(<ErrorRecovery />)
    expect(screen.getByRole('alert')).toHaveTextContent(
      'Your data has not been changed.',
    )
  })
})
