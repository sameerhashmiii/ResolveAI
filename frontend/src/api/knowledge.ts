import { ApiError, apiRequest } from './client'

export interface KnowledgeSearchItem {
  source_id: string
  document_id: string
  article_id: string
  title: string
  category: string
  heading: string | null
  excerpt: string
  relevance_score: number
  source_path: string
}

export interface KnowledgeSearchResponse {
  query: string
  embedding_model: string
  items: KnowledgeSearchItem[]
}

function isSearchItem(value: unknown): value is KnowledgeSearchItem {
  if (typeof value !== 'object' || value === null) return false
  const item = value as Record<string, unknown>
  return (
    typeof item.source_id === 'string' &&
    typeof item.document_id === 'string' &&
    typeof item.article_id === 'string' &&
    typeof item.title === 'string' &&
    typeof item.category === 'string' &&
    (typeof item.heading === 'string' || item.heading === null) &&
    typeof item.excerpt === 'string' &&
    typeof item.relevance_score === 'number' &&
    typeof item.source_path === 'string'
  )
}

function validateSearchResponse(value: unknown): KnowledgeSearchResponse {
  if (typeof value !== 'object' || value === null) {
    throw new ApiError('ResolveAI returned an invalid knowledge response.')
  }
  const response = value as Record<string, unknown>
  if (
    typeof response.query !== 'string' ||
    typeof response.embedding_model !== 'string' ||
    !Array.isArray(response.items) ||
    !response.items.every(isSearchItem)
  ) {
    throw new ApiError('ResolveAI returned an invalid knowledge response.')
  }
  return response as unknown as KnowledgeSearchResponse
}

export async function searchKnowledge(query: string, signal?: AbortSignal) {
  const params = new URLSearchParams({ q: query, top_k: '5' })
  const response = await apiRequest<unknown>(
    `/knowledge/search?${params.toString()}`,
    { signal },
  )
  return validateSearchResponse(response)
}
