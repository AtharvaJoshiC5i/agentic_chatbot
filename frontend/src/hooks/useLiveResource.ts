import { useEffect, useRef, useState } from 'react'
import { WORKSPACE_DASHBOARD_REFRESH } from '../lib/workspaceRefresh'

const POLL_MS = 20_000

/**
 * Loads a resource and keeps it fresh (poll + window focus + manual refresh).
 *
 * A background poll never starts a new request while one is still running, and a running request is never
 * discarded just because a poll interval elapsed: only a *newer* request supersedes an older one. (Previously every
 * poll cancelled the in-flight request, so a response slower than the poll interval never arrived.)
 */
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
  const requestSeq = useRef(0)
  const inFlight = useRef(false)
  const mounted = useRef(true)

  useEffect(() => {
    mounted.current = true
    return () => {
      mounted.current = false
    }
  }, [])

  // Explicit refresh (after a write) always fetches; the newest request wins.
  const refresh = () => setTick((n) => n + 1)

  useEffect(() => {
    const seq = ++requestSeq.current
    inFlight.current = true
    if (data === null) setLoading(true)
    setError(null)
    fetcher()
      .then((value) => {
        if (mounted.current && seq === requestSeq.current) setData(value)
      })
      .catch((e) => {
        if (mounted.current && seq === requestSeq.current) setError(e instanceof Error ? e.message : 'Refresh failed')
      })
      .finally(() => {
        if (seq !== requestSeq.current) return
        inFlight.current = false
        if (mounted.current) setLoading(false)
      })
    // eslint-disable-next-line react-hooks/exhaustive-deps -- caller deps + manual tick
  }, [...deps, tick])

  useEffect(() => {
    const poll = () => {
      if (!inFlight.current) setTick((n) => n + 1)
    }
    const timer = window.setInterval(poll, POLL_MS)
    window.addEventListener('focus', poll)
    window.addEventListener(WORKSPACE_DASHBOARD_REFRESH, poll)
    return () => {
      window.clearInterval(timer)
      window.removeEventListener('focus', poll)
      window.removeEventListener(WORKSPACE_DASHBOARD_REFRESH, poll)
    }
  }, [])

  return { data, loading, error, refresh }
}
