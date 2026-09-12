import type { JsonValue } from '../../api/types'

interface AggregateItem {
  key: string
  label: string
  value: string
}

const aggregateKey =
  /(accuracy|precision|recall|f1|rate|score|count|total|median|mean|average|percentile|latency|duration|error|success|failure|failed|pass|match|coverage)/i
const methodologyKey =
  /(method|version|evaluator|aggregation|threshold|strategy|framework|dataset|scoring|mode)/i
const hiddenKey =
  /(case|ticket|prompt|input|output|message|email|description|excerpt|content|customer|requester)/i

function labelFor(path: string[]) {
  return path
    .join(' / ')
    .replaceAll('_', ' ')
    .replace(/\b\w/g, (letter) => letter.toUpperCase())
}

function displayValue(key: string, value: string | number | boolean | null) {
  if (value === null) return 'Not reported'
  if (typeof value === 'boolean') return value ? 'Yes' : 'No'
  if (
    typeof value === 'number' &&
    /(accuracy|precision|recall|f1|rate|coverage)/i.test(key) &&
    value >= 0 &&
    value <= 1
  ) {
    return `${(value * 100).toFixed(1)}%`
  }
  return String(value)
}

function safeAggregates(value: JsonValue, mode: 'metrics' | 'methodology') {
  const items: AggregateItem[] = []
  const visit = (current: JsonValue, path: string[], depth: number) => {
    if (
      items.length >= 24 ||
      depth > 3 ||
      current === null ||
      Array.isArray(current) ||
      typeof current !== 'object'
    ) {
      return
    }

    Object.entries(current)
      .slice(0, 24)
      .forEach(([key, child]) => {
        if (items.length >= 24 || hiddenKey.test(key)) return
        const childPath = [...path, key]
        if (
          typeof child === 'object' &&
          child !== null &&
          !Array.isArray(child)
        ) {
          visit(child, childPath, depth + 1)
          return
        }
        const allowed =
          mode === 'metrics' ? aggregateKey.test(key) : methodologyKey.test(key)
        if (!allowed || typeof child === 'string') return
        if (
          typeof child === 'number' ||
          typeof child === 'boolean' ||
          child === null
        ) {
          items.push({
            key: childPath.join('.'),
            label: labelFor(childPath),
            value: displayValue(key, child),
          })
        }
      })
  }
  visit(value, [], 0)
  return items
}

export function SafeAggregateList({
  value,
  mode = 'metrics',
}: {
  value: JsonValue
  mode?: 'metrics' | 'methodology'
}) {
  const items = safeAggregates(value, mode)
  if (items.length === 0) {
    return <p className="aggregate-empty">No aggregate values were reported.</p>
  }

  return (
    <dl className="aggregate-list">
      {items.map((item) => (
        <div key={item.key}>
          <dt>{item.label}</dt>
          <dd>{item.value}</dd>
        </div>
      ))}
    </dl>
  )
}
