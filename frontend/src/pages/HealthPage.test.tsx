import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { getHealthReady, type HealthReadyResponse } from '../api/health'
import { HealthPage } from './HealthPage'

vi.mock('../api/health', async (importOriginal) => {
  const original = await importOriginal<typeof import('../api/health')>()
  return { ...original, getHealthReady: vi.fn() }
})

const mockedGetHealthReady = vi.mocked(getHealthReady)

function renderPage(children: ReactNode = <HealthPage />) {
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: Infinity },
    },
  })

  return render(
    <QueryClientProvider client={client}>{children}</QueryClientProvider>,
  )
}

afterEach(() => {
  vi.clearAllMocks()
})

describe('HealthPage', () => {
  it('shows a loading state while readiness is being checked', () => {
    mockedGetHealthReady.mockReturnValue(
      new Promise<HealthReadyResponse>(() => undefined),
    )

    renderPage()

    expect(screen.getByRole('status')).toHaveTextContent('Checking')
    expect(screen.getByTestId('loading-state')).toBeInTheDocument()
  })

  it('shows ready details from the health service', async () => {
    mockedGetHealthReady.mockResolvedValue({
      status: 'ready',
      service: 'ResolveAI API',
      timestamp: '2026-09-11T10:30:00Z',
    })

    renderPage()

    await screen.findByText('Ready')
    expect(screen.getByRole('status')).toHaveTextContent('Ready')
    expect(
      screen.getByText('The platform foundation is accepting traffic.'),
    ).toBeInTheDocument()
    expect(screen.getByText('ResolveAI API')).toBeInTheDocument()
  })

  it('shows a degraded state and can retry a failed request', async () => {
    const user = userEvent.setup()
    mockedGetHealthReady
      .mockRejectedValueOnce(
        new Error('The readiness service could not be reached.'),
      )
      .mockResolvedValueOnce({ status: 'ready' })

    renderPage()

    await screen.findByText('Degraded')
    expect(screen.getByRole('status')).toHaveTextContent('Degraded')
    expect(
      screen.getByText('The readiness service could not be reached.'),
    ).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Check again' }))

    await screen.findByText('Ready')
    expect(screen.getByRole('status')).toHaveTextContent('Ready')
    expect(mockedGetHealthReady).toHaveBeenCalledTimes(2)
  })

  it('treats a non-ready response as degraded', async () => {
    mockedGetHealthReady.mockResolvedValue({ status: 'degraded' })

    renderPage()

    await screen.findByText('Degraded')
    expect(screen.getByRole('status')).toHaveTextContent('Degraded')
    expect(screen.getByText(/service reported/i)).toHaveTextContent('degraded')
  })
})
