import { screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { renderApp } from '../test/renderApp'

describe('LandingPage', () => {
  it('presents the trust model, scenarios, and guided CTA publicly', () => {
    vi.spyOn(globalThis, 'fetch').mockReturnValue(
      new Promise<Response>(() => undefined),
    )
    renderApp('/')

    expect(
      screen.getByRole('heading', { name: 'Evidence first. Humans decide.' }),
    ).toBeInTheDocument()
    expect(
      screen.getByRole('link', { name: 'Start 90-second guided demo' }),
    ).toHaveAttribute('href', '/login?scenario=dallas-vpn-payrollpro-dns')
    expect(screen.getAllByRole('link', { name: 'Use scenario' })).toHaveLength(
      5,
    )
    expect(screen.getByText('No automated remediation')).toBeInTheDocument()
    expect(
      screen.getByText(/Workflow completion is not accuracy/),
    ).toBeInTheDocument()
  })
})
