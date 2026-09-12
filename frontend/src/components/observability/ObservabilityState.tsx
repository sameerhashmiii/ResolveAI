interface ObservabilityStateProps {
  title: string
  error?: Error | null
  onRetry?: () => void
}

export function ObservabilityState({
  title,
  error,
  onRetry,
}: ObservabilityStateProps) {
  if (!error) {
    return (
      <div className="observability-state" role="status">
        Loading {title.toLowerCase()}...
      </div>
    )
  }

  return (
    <div
      className="observability-state observability-state--error"
      role="alert"
    >
      <strong>{title} unavailable</strong>
      <p>{error.message}</p>
      {onRetry && (
        <button className="text-button" type="button" onClick={onRetry}>
          Try again
        </button>
      )}
    </div>
  )
}
