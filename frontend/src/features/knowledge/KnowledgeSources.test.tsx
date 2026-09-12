import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { TicketDetail } from '../../api/types'
import { jsonResponse, requestUrl, userResponse } from '../../test/renderApp'
import { buildKnowledgeQuery, KnowledgeSources } from './KnowledgeSources'

afterEach(() => vi.restoreAllMocks())

const ticket: TicketDetail = {
  id: 'ticket-42',
  ticket_number: 'RAI-1042',
  title: 'VPN access unavailable',
  description: 'Cannot connect from the London office.',
  requester_name: 'Private requester',
  requester_department: 'Private department',
  location: 'Private location',
  device: 'Private device',
  application: 'Secure VPN',
  category: 'network',
  priority: 'p2',
  status: 'new',
  assigned_to: null,
  created_by: userResponse.user,
  created_at: '2026-09-11T10:00:00Z',
  updated_at: '2026-09-11T10:00:00Z',
}

const exactExcerpt =
  'This persisted source excerpt explains the approved VPN recovery sequence in exact operational detail, including the checks an analyst should complete before resetting a profile. It remains guidance and must be reviewed in the context of the current request.'

const response = {
  query: 'ticket context',
  embedding_model: 'local-hash-v1',
  items: [
    {
      source_id: 'source-api-1',
      document_id: 'document-api-1',
      article_id: 'KB-104',
      title: 'Restore remote access',
      category: 'Remote Access',
      heading: 'Profile recovery',
      excerpt: exactExcerpt,
      relevance_score: 1.8,
      source_path: 'knowledge/remote-access.md',
    },
  ],
}

function renderKnowledge(children: ReactNode) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={client}>{children}</QueryClientProvider>,
  )
}

describe('KnowledgeSources', () => {
  it('builds a bounded query from only allowed ticket context', () => {
    const query = buildKnowledgeQuery({
      ...ticket,
      description: `Connection failure ${'x'.repeat(600)}`,
    })

    expect(query.length).toBe(500)
    expect(query).toContain('Title: VPN access unavailable')
    expect(query).toContain('Application: Secure VPN')
    expect(query).toContain('Category: network')
    expect(query).toContain('Description: Connection failure')
    expect(query).not.toContain('Private requester')
    expect(query).not.toContain('Private department')
    expect(query).not.toContain('Private location')
    expect(query).not.toContain('Private device')
  })

  it('shows loading and an honest empty state', async () => {
    let finishRequest!: (value: Response) => void
    vi.spyOn(globalThis, 'fetch').mockImplementation(
      () =>
        new Promise<Response>((resolve) => {
          finishRequest = resolve
        }),
    )
    renderKnowledge(<KnowledgeSources ticket={ticket} isAuthenticated={true} />)

    expect(screen.getByRole('status')).toHaveTextContent(
      'Searching knowledge sources...',
    )
    finishRequest(jsonResponse({ ...response, items: [] }))

    expect(
      await screen.findByRole('heading', {
        name: 'No relevant sources found.',
      }),
    ).toBeInTheDocument()
  })

  it('shows a safe error with a working retry', async () => {
    const fetchMock = vi
      .spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(jsonResponse({ detail: 'Sensitive detail' }, 500))
      .mockResolvedValueOnce(jsonResponse({ ...response, items: [] }))
    const user = userEvent.setup()
    renderKnowledge(<KnowledgeSources ticket={ticket} isAuthenticated={true} />)

    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent('Knowledge sources could not be loaded.')
    expect(alert).not.toHaveTextContent('Sensitive detail')
    await user.click(
      within(alert).getByRole('button', { name: 'Retry source search' }),
    )

    expect(
      await screen.findByRole('heading', {
        name: 'No relevant sources found.',
      }),
    ).toBeInTheDocument()
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })

  it('renders API source data and toggles the exact excerpt', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(jsonResponse(response))
    const user = userEvent.setup()
    renderKnowledge(<KnowledgeSources ticket={ticket} isAuthenticated={true} />)

    const heading = await screen.findByRole('heading', {
      name: 'Restore remote access',
    })
    const card = heading.closest('article')
    if (!card) throw new Error('Source card was not rendered.')
    expect(within(card).getByText('KB-104')).toBeInTheDocument()
    expect(within(card).getByText('Remote Access')).toBeInTheDocument()
    expect(within(card).getByText('100% relevant')).toBeInTheDocument()
    expect(
      within(card).getByText('source-api-1 / document-api-1'),
    ).toBeInTheDocument()
    expect(
      screen.getByText('Local retrieval / local-hash-v1'),
    ).toBeInTheDocument()
    expect(within(card).queryByText(exactExcerpt)).not.toBeInTheDocument()
    expect(screen.queryByText(/AI verified/i)).not.toBeInTheDocument()
    expect(
      screen.queryByText(/root cause identified|proves? the root cause/i),
    ).not.toBeInTheDocument()
    expect(screen.getByText(/not proof of root cause/i)).toBeInTheDocument()

    await user.click(
      within(card).getByRole('button', { name: 'View relevant excerpt' }),
    )
    expect(within(card).getByText(exactExcerpt)).toBeInTheDocument()
    await user.click(within(card).getByRole('button', { name: 'Hide excerpt' }))
    expect(within(card).queryByText(exactExcerpt)).not.toBeInTheDocument()
  })

  it('does not request sources while unauthenticated', () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch')
    renderKnowledge(
      <KnowledgeSources ticket={ticket} isAuthenticated={false} />,
    )
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('sends the bounded ticket context in the search request', async () => {
    let capturedInput: RequestInfo | URL | undefined
    vi.spyOn(globalThis, 'fetch').mockImplementation((input) => {
      capturedInput = input
      return Promise.resolve(jsonResponse({ ...response, items: [] }))
    })
    renderKnowledge(
      <KnowledgeSources
        ticket={{ ...ticket, description: `Failure ${'x'.repeat(600)}` }}
        isAuthenticated={true}
      />,
    )
    await screen.findByRole('heading', { name: 'No relevant sources found.' })

    if (!capturedInput) throw new Error('Expected a knowledge search request.')
    const url = new URL(requestUrl(capturedInput), 'http://localhost')
    const sentQuery = url.searchParams.get('q') ?? ''
    expect(sentQuery.length).toBe(500)
    expect(sentQuery).toContain('Title: VPN access unavailable')
    expect(url.search).toContain('%0A')
  })
})
