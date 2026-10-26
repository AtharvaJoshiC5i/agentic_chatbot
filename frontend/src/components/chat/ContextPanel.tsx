import { Loader2, X } from 'lucide-react'
import { useEffect, useState } from 'react'
import { api } from '../../api/client'
import type {
  InvestigationReportOut,
  RefundableAmountOut,
  TimelineEventOut,
} from '../../api/types'
import { formatInrFromPaise, formatDateTime, humanize } from '../../lib/format'
import { panelTitle, workspaceIconButton } from '../ui/styles'
import { ContextPanelWorkflow } from './ContextPanelWorkflow'

function SectionTitle({ children }: { children: React.ReactNode }) {
  return <h3 className={panelTitle}>{children}</h3>
}

export function ContextPanel({
  returnId,
  onClose,
}: {
  returnId: string
  onClose: () => void
}) {
  const [investigation, setInvestigation] = useState<InvestigationReportOut | null>(null)
  const [timeline, setTimeline] = useState<TimelineEventOut[]>([])
  const [refundable, setRefundable] = useState<RefundableAmountOut | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [reloadKey, setReloadKey] = useState(0)

  useEffect(() => {
    setLoading(true)
    setError(null)

    Promise.all([
      api.getInvestigation(returnId),
      api.getTimeline(returnId, true),
      api.getRefundableAmount(returnId),
    ])
      .then(([inv, tl, ref]) => {
        setInvestigation(inv)
        setTimeline(tl.slice(-5).reverse())
        setRefundable(ref)
      })
      .catch((e) => setError(e instanceof Error ? e.message : 'Could not load context'))
      .finally(() => setLoading(false))
  }, [returnId, reloadKey])

  const windowState = investigation?.f3_policy.within_return_window

  return (
    <aside
      className="flex w-full flex-col border-l border-stone-200/90 bg-white/95 backdrop-blur-sm"
      aria-label="Return context"
    >
      <div className="workspace-header flex h-12 shrink-0 items-center justify-between px-4">
        <div className="flex items-baseline gap-2">
          <span className="font-mono text-sm font-semibold text-stone-900">{returnId}</span>
          <span className="text-xs text-stone-500">Return context</span>
        </div>
        <button type="button" className={workspaceIconButton} onClick={onClose} aria-label="Close panel">
          <X className="size-4" strokeWidth={1.75} />
        </button>
      </div>

      <div className="flex-1 space-y-7 overflow-x-hidden overflow-y-auto p-4">
        {loading && (
          <div className="flex items-center gap-2 text-sm text-stone-500" role="status">
            <Loader2 className="size-4 animate-spin" aria-hidden />
            Loading context…
          </div>
        )}
        {error && (
          <p className="rounded-lg border border-red-200 bg-red-50 px-3 py-2.5 text-sm text-red-700" role="alert">
            {error}
          </p>
        )}

        {!loading && (
          <ContextPanelWorkflow returnId={returnId} onChanged={() => setReloadKey((k) => k + 1)} />
        )}

        {refundable && !loading && (
          <section>
            <SectionTitle>Refundable amount</SectionTitle>
            <dl className="mt-3 divide-y divide-stone-100 rounded-lg border border-stone-200 text-sm">
              <div className="flex justify-between px-3 py-2.5">
                <dt className="text-stone-500">Line total</dt>
                <dd className="font-medium tabular-nums text-stone-900">
                  {formatInrFromPaise(refundable.line_total_paise)}
                </dd>
              </div>
              <div className="flex justify-between px-3 py-2.5">
                <dt className="text-stone-500">Already refunded</dt>
                <dd className="font-medium tabular-nums text-stone-900">
                  {formatInrFromPaise(refundable.already_refunded_paise)}
                </dd>
              </div>
              <div className="flex justify-between px-3 py-2.5 bg-accent-50/50">
                <dt className="font-medium text-stone-700">Remaining</dt>
                <dd className="font-semibold tabular-nums text-accent-800">
                  {formatInrFromPaise(refundable.remaining_refundable_paise)}
                </dd>
              </div>
            </dl>
          </section>
        )}

        {investigation && !loading && (
          <section>
            <SectionTitle>Investigation</SectionTitle>
            <dl className="mt-3 divide-y divide-stone-100 rounded-lg border border-stone-200 text-sm">
              <div className="px-3 py-2.5">
                <dt className="text-xs text-stone-500">Outcome</dt>
                <dd className="mt-0.5 font-medium text-stone-900">{humanize(investigation.f4_outcome)}</dd>
              </div>
              <div className="px-3 py-2.5">
                <dt className="text-xs text-stone-500">Signal</dt>
                <dd className="mt-0.5 font-medium text-stone-900">{humanize(investigation.f2_signal)}</dd>
              </div>
              <div className="px-3 py-2.5">
                <dt className="text-xs text-stone-500">Return window</dt>
                <dd className="mt-1">
                  {windowState == null ? (
                    <span className="text-stone-500">Not determined</span>
                  ) : (
                    <span
                      className={`inline-flex items-center gap-1.5 rounded-md px-2 py-0.5 text-xs font-medium ${
                        windowState ? 'bg-emerald-50 text-emerald-700' : 'bg-amber-50 text-amber-700'
                      }`}
                    >
                      <span
                        className={`size-1.5 rounded-full ${windowState ? 'bg-emerald-500' : 'bg-amber-500'}`}
                        aria-hidden
                      />
                      {windowState ? 'Inside window' : 'Outside window'}
                    </span>
                  )}
                </dd>
              </div>
            </dl>
          </section>
        )}

        {timeline.length > 0 && !loading && (
          <section>
            <SectionTitle>Recent timeline</SectionTitle>
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
          </section>
        )}
      </div>
    </aside>
  )
}
