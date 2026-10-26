import { useEffect, useState } from 'react'

const POLL_MS = 20_000

export function useLiveResource<T>(fetcher: () => Promise<T>, deps: unknown[]): {
  data: T | null
  loading: boolean
  error: string | null
  refresh: () => void
} {
  const [data, setData] = useState<T | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [tick, setTick] = useState(0)

  const refresh = () => setTick((n) => n + 1)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    fetcher()
      .then((value) => {
        if (!cancelled) setData(value)
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof Error ? e.message : 'Refresh failed')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    const timer = window.setInterval(() => setTick((n) => n + 1), POLL_MS)
    const onFocus = () => setTick((n) => n + 1)
    window.addEventListener('focus', onFocus)
    return () => {
      cancelled = true
      window.clearInterval(timer)
      window.removeEventListener('focus', onFocus)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- caller deps + manual tick
  }, [...deps, tick])

  return { data, loading, error, refresh }
}
