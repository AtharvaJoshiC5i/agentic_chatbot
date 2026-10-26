import { Activity, Loader2, RefreshCw } from 'lucide-react'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, Navigate } from 'react-router-dom'
import { api } from '../api/client'
import type { MonitoringSummaryOut, SystemAlertOut } from '../api/types'
import { WorkspaceNav } from '../components/layout/WorkspaceNav'
import { Badge } from '../components/ui/Badge'
import { useAuth } from '../context/AuthContext'
import { formatDateTime, humanize } from '../lib/format'
import { button, panelTitle } from '../components/ui/styles'

function severityTone(severity: string): 'danger' | 'warning' | 'neutral' | 'accent' {
  if (severity === 'critical') return 'danger'
  if (severity === 'high') return 'danger'
  if (severity === 'warning') return 'warning'
  if (severity === 'info') return 'neutral'
  return 'accent'
}

function AlertRow({
  alert,
  canAcknowledge,
  onAcknowledge,
  busy,
}: {
  alert: SystemAlertOut
  canAcknowledge: boolean
  onAcknowledge: (id: number) => void
  busy: boolean
}) {
  const returnLink =
    alert.related_entity === 'return'
      ? `/workspace?return=${encodeURIComponent(alert.related_id)}`
      : null

  return (
    <li className="rounded-xl border border-stone-200 bg-white px-4 py-3.5 shadow-sm transition-shadow hover:shadow-md">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 flex-1 space-y-1.5">
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone={severityTone(alert.severity)}>{alert.severity}</Badge>
            <span className="text-sm font-medium text-stone-900">{humanize(alert.alert_type)}</span>
          </div>
          <p className="text-sm text-stone-600">
            <span className="text-stone-500">{humanize(alert.related_entity)}</span>{' '}
            <span className="font-mono font-medium text-stone-800">{alert.related_id}</span>
          </p>
          <time className="block text-xs text-stone-400">{formatDateTime(alert.created_at)}</time>
        </div>
        <div className="flex shrink-0 flex-wrap gap-2">
          {returnLink && (
            <Link to={returnLink} className={button('secondary', 'sm')}>
              Open in agent
            </Link>
          )}
          {canAcknowledge && alert.status === 'open' && (
            <button
              type="button"
              className={button('ghost', 'sm')}
              disabled={busy}
              onClick={() => onAcknowledge(alert.alert_id)}
            >
              Acknowledge
            </button>
          )}
        </div>
      </div>
    </li>
  )
}

export function MonitoringPage() {
  const { role } = useAuth()
  const isSupervisor = role?.includes('supervisor') || role?.includes('administrator')
  if (!isSupervisor) {
    return <Navigate to="/workspace/dashboard" replace />
  }
  return <MonitoringPageContent role={role} />
}

function MonitoringPageContent({ role }: { role: string | null }) {
  const [summary, setSummary] = useState<MonitoringSummaryOut | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [ackBusyId, setAckBusyId] = useState<number | null>(null)

  const canRun = role?.includes('supervisor') || role?.includes('administrator')
  const canAcknowledge = canRun

  const byType = useMemo(() => {
    const map = new Map<string, number>()
    for (const a of summary?.alerts ?? []) {
      map.set(a.alert_type, (map.get(a.alert_type) ?? 0) + 1)
    }
    return [...map.entries()].sort((a, b) => b[1] - a[1])
  }, [summary])

  const load = useCallback(async () => {
    setError(null)
    setLoading(true)
    try {
      const data = await api.monitoringSummary()
      setSummary(data)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load monitoring summary')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  async function runChecks() {
    if (!canRun) return
    setBusy(true)
    setError(null)
    try {
      await api.runMonitoring()
      await load()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Monitoring run failed')
    } finally {
      setBusy(false)
    }
  }

  async function acknowledge(alertId: number) {
    if (!canAcknowledge) return
    setAckBusyId(alertId)
    try {
      await api.acknowledgeAlert(alertId)
      await load()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not acknowledge alert')
    } finally {
      setAckBusyId(null)
    }
  }

  return (
    <div className="workspace-shell flex h-dvh flex-col overflow-hidden font-sans text-stone-900">
      <WorkspaceNav />
      <div className="shrink-0 border-b border-stone-200 bg-white px-4 py-6 sm:px-6">
        <p className={panelTitle}>Operations</p>
        <div className="mt-1 flex flex-wrap items-center gap-3">
          <h1 className="text-xl font-semibold text-stone-900">Monitoring</h1>
          <Activity className="size-5 text-accent-600" strokeWidth={1.75} aria-hidden />
        </div>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-stone-600">
          Overdue investigations, pending approvals, stalled recovery tasks, and other signals the
          backend tracks with deduplicated alerts.
        </p>
        <div className="mt-4 flex flex-wrap items-center gap-2">
          <button
            type="button"
            className={button('secondary', 'sm')}
            disabled={loading}
            onClick={() => load()}
          >
            <RefreshCw className={`size-4 ${loading ? 'animate-spin' : ''}`} aria-hidden />
            Refresh
          </button>
          {canRun && (
            <button type="button" className={button('primary', 'sm')} disabled={busy} onClick={runChecks}>
              {busy ? 'Running checks…' : 'Run checks now'}
            </button>
          )}
        </div>
      </div>

      <main className="flex-1 overflow-y-auto px-4 py-6 sm:px-6">
        <div className="mx-auto max-w-4xl space-y-6">
          {error && (
            <p className="rounded-lg border border-red-200 bg-red-50 px-3 py-2.5 text-sm text-red-700" role="alert">
              {error}
            </p>
          )}

          <div className="grid gap-3 sm:grid-cols-3">
            <div className="rounded-xl border border-stone-200 bg-white px-4 py-3 shadow-sm">
              <p className="text-xs font-medium uppercase tracking-wide text-stone-500">Open alerts</p>
              <p className="mt-1 text-2xl font-semibold tabular-nums text-stone-900">
                {loading ? '—' : summary?.open_alerts ?? 0}
              </p>
            </div>
            <div className="rounded-xl border border-stone-200 bg-white px-4 py-3 shadow-sm sm:col-span-2">
              <p className="text-xs font-medium uppercase tracking-wide text-stone-500">By type</p>
              {byType.length === 0 ? (
                <p className="mt-2 text-sm text-stone-500">No open alerts</p>
              ) : (
                <ul className="mt-2 flex flex-wrap gap-2">
                  {byType.map(([type, count]) => (
                    <li
                      key={type}
                      className="rounded-md bg-stone-100 px-2.5 py-1 text-xs font-medium text-stone-700"
                    >
                      {humanize(type)} <span className="tabular-nums text-stone-500">({count})</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>

          {loading && !summary && (
            <div className="flex items-center gap-2 text-sm text-stone-500" role="status">
              <Loader2 className="size-4 animate-spin" aria-hidden />
              Loading alerts…
            </div>
          )}

          <ul className="space-y-3">
            {(summary?.alerts ?? []).map((alert) => (
              <AlertRow
                key={alert.alert_id}
                alert={alert}
                canAcknowledge={Boolean(canAcknowledge)}
                busy={ackBusyId === alert.alert_id}
                onAcknowledge={acknowledge}
              />
            ))}
          </ul>

          {!loading && !summary?.alerts?.length && !error && (
            <div className="rounded-xl border border-dashed border-stone-200 bg-stone-50/80 px-6 py-10 text-center">
              <p className="text-sm font-medium text-stone-800">All clear</p>
              <p className="mt-1 text-sm text-stone-500">
                No open monitoring alerts. Supervisors can run checks to refresh signals.
              </p>
            </div>
          )}
        </div>
      </main>
    </div>
  )
}
