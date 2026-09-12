import { useQuery } from '@tanstack/react-query'
import { useId, useState } from 'react'

import { searchKnowledge, type KnowledgeSearchItem } from '../../api/knowledge'
import type { TicketDetail } from '../../api/types'

interface KnowledgeSourcesProps {
  ticket: TicketDetail
  isAuthenticated: boolean
}

const MAX_QUERY_LENGTH = 500
const PREVIEW_LENGTH = 180

export function buildKnowledgeQuery(ticket: TicketDetail) {
  const context: Array<[string, string | null | undefined]> = [
    ['Title', ticket.title],
    ['Application', ticket.application],
    ['Category', ticket.category],
    ['Description', ticket.description],
  ]

  return context
    .flatMap(([label, value]) =>
      typeof value === 'string' && value.trim()
        ? [`${label}: ${value.trim()}`]
        : [],
    )
    .join('\n')
    .slice(0, MAX_QUERY_LENGTH)
}

function relevancePercentage(score: number) {
  if (!Number.isFinite(score)) return 0
  return Math.round(Math.min(1, Math.max(0, score)) * 100)
}

function ExcerptPreview({ excerpt }: { excerpt: string }) {
  const truncated = excerpt.length > PREVIEW_LENGTH
  const preview = excerpt.slice(0, PREVIEW_LENGTH).trimEnd()
  return (
    <p>
      {preview ? `${preview}${truncated ? '...' : ''}` : 'Excerpt available.'}
    </p>
  )
}

function SourceCard({ item }: { item: KnowledgeSearchItem }) {
  const [isExpanded, setIsExpanded] = useState(false)
  const excerptId = useId()

  return (
    <article className="knowledge-source-card">
      <div className="knowledge-source-topline">
        <span className="knowledge-article-id">{item.article_id}</span>
        <strong>{relevancePercentage(item.relevance_score)}% relevant</strong>
      </div>
      <h3>{item.title}</h3>
      <div className="knowledge-source-tags">
        <span>{item.category}</span>
        {item.heading && <span>{item.heading}</span>}
      </div>
      {!isExpanded && (
        <div id={excerptId} className="knowledge-excerpt-preview">
          <ExcerptPreview excerpt={item.excerpt} />
        </div>
      )}
      {isExpanded && (
        <blockquote id={excerptId} className="knowledge-excerpt">
          {item.excerpt}
        </blockquote>
      )}
      <button
        className="text-button knowledge-excerpt-toggle"
        type="button"
        aria-expanded={isExpanded}
        aria-controls={excerptId}
        onClick={() => setIsExpanded((value) => !value)}
      >
        {isExpanded ? 'Hide excerpt' : 'View relevant excerpt'}
      </button>
      <dl className="knowledge-provenance">
        <div>
          <dt>Source</dt>
          <dd>{item.source_path}</dd>
        </div>
        <div>
          <dt>Records</dt>
          <dd>
            {item.source_id} / {item.document_id}
          </dd>
        </div>
      </dl>
    </article>
  )
}

export function KnowledgeSources({
  ticket,
  isAuthenticated,
}: KnowledgeSourcesProps) {
  const query = buildKnowledgeQuery(ticket)
  const search = useQuery({
    queryKey: ['knowledge', 'search', ticket.id, query],
    queryFn: ({ signal }) => searchKnowledge(query, signal),
    enabled: isAuthenticated && query.length >= 2,
  })

  return (
    <section
      className="content-card knowledge-card"
      aria-labelledby="knowledge-sources-title"
    >
      <div className="section-heading knowledge-heading">
        <div>
          <p className="section-label">Retrieved guidance</p>
          <h2 id="knowledge-sources-title">Knowledge Sources</h2>
        </div>
        {search.data && (
          <span className="knowledge-model">
            Local retrieval / {search.data.embedding_model}
          </span>
        )}
      </div>

      <p className="knowledge-disclaimer">
        These sources are retrieved guidance, not proof of root cause. Review
        their relevance before using them to support ticket handling.
      </p>

      {search.isPending && isAuthenticated && (
        <div className="knowledge-loading" role="status">
          <span>Searching knowledge sources...</span>
          <div className="knowledge-skeleton" aria-hidden="true" />
          <div className="knowledge-skeleton" aria-hidden="true" />
        </div>
      )}
      {search.isError && (
        <div className="knowledge-state knowledge-state--error" role="alert">
          <strong>Knowledge sources could not be loaded.</strong>
          <p>The retrieval service may be temporarily unavailable.</p>
          <button
            className="button button--outline"
            type="button"
            onClick={() => void search.refetch()}
          >
            Retry source search
          </button>
        </div>
      )}
      {search.data && search.data.items.length === 0 && (
        <div className="empty-state empty-state--compact">
          <h3>No relevant sources found.</h3>
          <p>
            The knowledge base did not return guidance for this ticket context.
          </p>
        </div>
      )}
      {search.data && search.data.items.length > 0 && (
        <div className="knowledge-source-list">
          {search.data.items.map((item) => (
            <SourceCard
              key={`${item.source_id}:${item.document_id}`}
              item={item}
            />
          ))}
        </div>
      )}
    </section>
  )
}
