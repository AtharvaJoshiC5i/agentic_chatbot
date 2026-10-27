import { Loader2, X } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { api } from '../../api/client'
import type { TimelineEventOut } from '../../api/types'
import { formatDateTime, humanize } from '../../lib/format'
import { panelTitle, workspaceIconButton } from '../ui/styles'
import { ContextPanelWorkflow } from './ContextPanelWorkflow'

function SectionTitle({ children }: { children: React.ReactNode }) {
  return <h3 className={panelTitle}>{children}</h3>
}

export function ContextPanel({
  returnId,
  refreshKey = 0,
  onClose,
}: {
  returnId: string
  refreshKey?: number
  onClose: () => void
}) {
  const [timeline, setTimeline] = useState<TimelineEventOut[]>([])
  const [timelineLoading, setTimelineLoading] = useState(true)
  const [timelineRefreshing, setTimelineRefreshing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const requestSeq = useRef(0)

  useEffect(() => {
    const seq = ++requestSeq.current
    let cancelled = false
    const hasTimeline = timeline.length > 0
    if (!hasTimeline) setTimelineLoading(true)
    else setTimelineRefreshing(true)
    setError(null)

    api
      .getTimeline(returnId, true)
      .then((tl) => {
        if (cancelled || seq !== requestSeq.current) return
        setTimeline([...tl].reverse())
      })
      .catch((e) => {
        if (cancelled || seq !== requestSeq.current) return
        setError(e instanceof Error ? e.message : 'Could not load context')
      })
      .finally(() => {
        if (cancelled || seq !== requestSeq.current) return
        setTimelineLoading(false)
        setTimelineRefreshing(false)
      })

    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- refreshKey refetch; timeline length for UX only
  }, [returnId, refreshKey])

  return (
    <aside
      className="flex w-full flex-col border-l border-stone-200/90 bg-white/95 backdrop-blur-sm"
      aria-label="Return context"
    >
      <div className="workspace-header flex h-12 shrink-0 items-center justify-between px-4">
        <div className="flex items-baseline gap-2">
          <span className="font-mono text-sm font-semibold text-stone-900">{returnId}</span>
          <span className="text-xs text-stone-500">Case</span>
        </div>
        <button type="button" className={workspaceIconButton} onClick={onClose} aria-label="Close panel">
          <X className="size-4" strokeWidth={1.75} />
        </button>
      </div>

      <div className="flex-1 space-y-7 overflow-x-hidden overflow-y-auto p-4">
        <ContextPanelWorkflow returnId={returnId} refreshKey={refreshKey} />

        {error && (
          <p className="rounded-lg border border-red-200 bg-red-50 px-3 py-2.5 text-sm text-red-700" role="alert">
            {error}
          </p>
        )}

        <section aria-live="polite">
          <div className="flex items-center justify-between gap-2">
            <SectionTitle>Timeline</SectionTitle>
            {timelineRefreshing && (
              <Loader2 className="size-3.5 animate-spin text-stone-400" aria-label="Refreshing timeline" />
            )}
          </div>
          {timelineLoading && timeline.length === 0 && (
            <div className="mt-3 flex items-center gap-2 text-sm text-stone-500" role="status">
              <Loader2 className="size-4 animate-spin" aria-hidden />
              Loading timeline…
            </div>
          )}
          {timeline.length > 0 && (
            <ol className="mt-3 space-y-5 border-l border-stone-200 pl-4">
              {timeline.map((ev) => (
                <li key={ev.event_id} className="relative min-w-0">
                  <span
                    className="absolute top-1.5 -left-[21px] size-2.5 rounded-full border-2 border-white bg-stone-400 ring-1 ring-stone-200"
                    aria-hidden
                  />
                  <p className="text-sm font-medium text-stone-900">{humanize(ev.event_type)}</p>
                  <p className="mt-0.5 text-sm leading-5 text-stone-600 [overflow-wrap:anywhere]">
                    {ev.description}
                  </p>
                  <time className="mt-1 block text-xs text-stone-400">{formatDateTime(ev.event_timestamp)}</time>
                </li>
              ))}
            </ol>
          )}
          {!timelineLoading && timeline.length === 0 && !error && (
            <p className="mt-3 text-xs text-stone-500">No timeline events yet.</p>
          )}
        </section>
      </div>
    </aside>
  )
}
