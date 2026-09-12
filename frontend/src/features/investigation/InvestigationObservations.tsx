import type { InvestigationStep } from '../../api/types'

type JsonRecord = Record<string, unknown>

const blockedFields =
  /ground.?truth|cause|recommend|confidence|hidden|private|secret|internal/i

function isRecord(value: unknown): value is JsonRecord {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function text(value: unknown) {
  return typeof value === 'string' && value.trim() ? value : null
}

function number(value: unknown) {
  return typeof value === 'number' && Number.isFinite(value) ? value : null
}

function humanize(value: string) {
  return value
    .replaceAll('_', ' ')
    .replace(/\b\w/g, (letter) => letter.toUpperCase())
}

function records(result: unknown, keys: string[]): JsonRecord[] {
  if (!isRecord(result)) return []
  for (const key of keys) {
    const value = result[key]
    if (Array.isArray(value)) {
      const entries = value.filter(isRecord)
      if (entries.length > 0) return entries
      continue
    }
    if (isRecord(value)) {
      const nested = records(value, keys)
      return nested.length > 0 ? nested : [value]
    }
  }
  return Object.values(result).some(Array.isArray) ? [] : [result]
}

function displayValue(key: string, value: unknown): string | null {
  if (blockedFields.test(key)) return null
  if (typeof value === 'string' && value.trim()) return value
  if (typeof value === 'number' && Number.isFinite(value)) return String(value)
  if (typeof value === 'boolean') {
    if (key.toLowerCase().includes('synthetic'))
      return value ? 'Synthetic' : 'Not synthetic'
    return value ? 'Yes' : 'No'
  }
  if (
    Array.isArray(value) &&
    value.length > 0 &&
    value.every((item) => typeof item === 'string' || typeof item === 'number')
  )
    return value.join(', ')
  return null
}

function FactCard({ item }: { item: JsonRecord }) {
  const title =
    text(item.title) ??
    text(item.name) ??
    text(item.service) ??
    text(item.metric) ??
    text(item.event_type)
  const values = Object.entries(item).flatMap(([key, value]) => {
    const shown = displayValue(key, value)
    return shown === null || shown === title ? [] : [[key, shown] as const]
  })

  if (!title && values.length === 0) return null
  return (
    <article className="observation-card">
      {title && <h4>{title}</h4>}
      {values.length > 0 && (
        <dl className="observation-facts">
          {values.map(([key, value]) => (
            <div key={key}>
              <dt>{humanize(key)}</dt>
              <dd>{value}</dd>
            </div>
          ))}
        </dl>
      )}
    </article>
  )
}

function SimilarTicketCard({ item }: { item: JsonRecord }) {
  const sourceId = text(item.source_id)
  const title = text(item.title)
  if (!sourceId || !title) return null
  const similarity = number(item.similarity)
  const resolutionMinutes = number(item.resolution_time_minutes)
  const percentage =
    similarity === null
      ? null
      : Math.round(
          Math.min(
            100,
            Math.max(0, similarity <= 1 ? similarity * 100 : similarity),
          ),
        )

  return (
    <article className="similar-ticket-card">
      <div className="similar-ticket-topline">
        <strong>{sourceId}</strong>
        {percentage !== null && <span>{percentage}% similar</span>}
      </div>
      <h4>{title}</h4>
      <div className="observation-tags">
        {text(item.category) && <span>{text(item.category)}</span>}
        {text(item.priority) && <span>{text(item.priority)}</span>}
      </div>
      {text(item.resolution) && (
        <p className="similar-resolution">{text(item.resolution)}</p>
      )}
      {resolutionMinutes !== null && (
        <small>{resolutionMinutes} minutes to resolution</small>
      )}
    </article>
  )
}

type ObservationKind =
  | 'knowledge'
  | 'similar'
  | 'status'
  | 'telemetry'
  | 'logs'
  | 'incident'
  | 'history'
  | 'unknown'

function observationKind(toolName: string): ObservationKind {
  const value = toolName.toLowerCase()
  if (value.includes('knowledge')) return 'knowledge'
  if (value.includes('similar')) return 'similar'
  if (value.includes('telemetry') || value.includes('metric'))
    return 'telemetry'
  if (value.includes('log')) return 'logs'
  if (value.includes('incident')) return 'incident'
  if (value.includes('event') || value.includes('history')) return 'history'
  if (value.includes('status') || value.includes('service')) return 'status'
  return 'unknown'
}

const sectionConfig: Record<
  Exclude<ObservationKind, 'knowledge' | 'unknown'>,
  { title: string; keys: string[] }
> = {
  similar: {
    title: 'Similar Tickets',
    keys: ['items', 'similar_tickets', 'tickets', 'results'],
  },
  status: {
    title: 'System Status',
    keys: [
      'services',
      'components',
      'service_status',
      'items',
      'results',
      'status',
    ],
  },
  telemetry: {
    title: 'Telemetry',
    keys: [
      'observations',
      'records',
      'telemetry',
      'items',
      'results',
      'summary',
    ],
  },
  logs: {
    title: 'Logs',
    keys: ['logs', 'records', 'entries', 'items', 'events', 'results'],
  },
  incident: {
    title: 'Related Incident',
    keys: [
      'related_incident',
      'incidents',
      'incident',
      'public_facts',
      'items',
      'results',
    ],
  },
  history: {
    title: 'Ticket History',
    keys: ['events', 'ticket_events', 'history', 'items', 'results'],
  },
}

export function InvestigationObservation({
  step,
}: {
  step: InvestigationStep
}) {
  if (!step.tool_name) return null
  const kind = observationKind(step.tool_name)
  if (kind === 'unknown') return null
  if (kind === 'knowledge') {
    return (
      <section
        className="observation-section"
        aria-labelledby={`result-${step.id}`}
      >
        <h3 id={`result-${step.id}`}>Knowledge Sources</h3>
        <p className="muted">
          {step.source_count > 0
            ? `${String(step.source_count)} source${step.source_count === 1 ? '' : 's'} collected. See Knowledge Sources above for the retrieved guidance.`
            : 'No knowledge sources were collected.'}
        </p>
      </section>
    )
  }

  const config = sectionConfig[kind]
  const items = records(step.result, config.keys)
  const usableItems =
    kind === 'similar'
      ? items.filter((item) => text(item.source_id) && text(item.title))
      : items.filter((item) =>
          Object.entries(item).some(
            ([key, value]) => displayValue(key, value) !== null,
          ),
        )

  return (
    <section
      className="observation-section"
      aria-labelledby={`result-${step.id}`}
    >
      <h3 id={`result-${step.id}`}>{config.title}</h3>
      {usableItems.length === 0 ? (
        <p className="observation-unavailable">Observation data unavailable.</p>
      ) : (
        <div className="observation-grid">
          {usableItems.map((item, index) =>
            kind === 'similar' ? (
              <SimilarTicketCard
                key={`${text(item.source_id) ?? 'similar'}-${String(index)}`}
                item={item}
              />
            ) : (
              <FactCard key={String(index)} item={item} />
            ),
          )}
        </div>
      )}
    </section>
  )
}
