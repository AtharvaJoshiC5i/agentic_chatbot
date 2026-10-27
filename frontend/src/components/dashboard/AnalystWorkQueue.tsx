import { useMemo, useState } from 'react'
import type { WorkspaceDashboardOut, WorkspaceQueueItem } from '../../api/types'
import { analystAgentPrompt } from '../../lib/workflowAgent'
import { humanize } from '../../lib/format'
import { button } from '../ui/styles'
import { Badge } from '../ui/Badge'
import { AskAgentLink } from './AskAgentLink'
import { QueueUpdateHint } from './QueueUpdateHint'
import { DeclineForm, NotificationReview } from './RowActions'

const STAGE_FILTERS: { id: string; label: string; match: (s: string) => boolean }[] = [
  { id: 'all', label: 'All', match: () => true },
  { id: 'investigate', label: 'Investigate', match: (s) => s === 'investigate' },
  { id: 'warehouse', label: 'Warehouse', match: (s) => s === 'await_warehouse' },
  { id: 'decline', label: 'To decline', match: (s) => s === 'decline_request' },
  { id: 'submit', label: 'Submit to supervisor', match: (s) => s === 'submit_refund' || s === 'submit_replacement' },
  { id: 'supervisor', label: 'Supervisor', match: (s) => s === 'await_supervisor' },
  { id: 'customer', label: 'Customer message', match: (s) => s === 'customer_follow_up' },
]

function stageTone(stage: string | null | undefined): 'accent' | 'warning' | 'neutral' | 'danger' {
  if (stage === 'await_supervisor') return 'warning'
  if (stage === 'submit_refund' || stage === 'submit_replacement') return 'accent'
  if (stage === 'await_warehouse') return 'warning'
  if (stage === 'decline_request') return 'danger'
  if (stage === 'customer_follow_up') return 'accent'
  return 'neutral'
}

export function AnalystWorkQueue({ data, onRefresh }: { data: WorkspaceDashboardOut; onRefresh: () => void }) {
  const [filter, setFilter] = useState('all')
  const queue = data.sections.find((s) => s.key === 'work_queue')?.items ?? []

  const filtered = useMemo(() => {
    const rule = STAGE_FILTERS.find((f) => f.id === filter) ?? STAGE_FILTERS[0]
    return queue.filter((row) => rule.match(row.workflow_stage ?? ''))
  }, [filter, queue])

  return (
    <section aria-labelledby="analyst-queue-title">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 id="analyst-queue-title" className="text-sm font-semibold text-stone-900">
            Return requests
          </h2>
          <p className="mt-0.5 text-xs text-stone-500">
            Policy check → inspection case or policy decline → warehouse verdict → supervisor → customer message.
          </p>
        </div>
      </div>

      <div className="mt-4 flex flex-wrap gap-1.5" role="tablist" aria-label="Filter queue">
        {STAGE_FILTERS.map((f) => (
          <button
            key={f.id}
            type="button"
            role="tab"
            aria-selected={filter === f.id}
            className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
              filter === f.id
                ? 'bg-stone-900 text-white'
                : 'bg-stone-100 text-stone-600 hover:bg-stone-200'
            }`}
            onClick={() => setFilter(f.id)}
          >
            {f.label}
          </button>
        ))}
      </div>

      <div className="mt-4 overflow-hidden rounded-xl border border-stone-200 bg-white shadow-sm">
        <table className="min-w-full text-left text-sm">
          <thead className="border-b border-stone-100 bg-stone-50/80 text-xs font-medium uppercase tracking-wide text-stone-500">
            <tr>
              <th className="px-4 py-3 font-medium">Return</th>
              <th className="hidden px-4 py-3 font-medium sm:table-cell">Ask</th>
              <th className="px-4 py-3 font-medium">Stage</th>
              <th className="hidden px-4 py-3 font-medium md:table-cell">Next step</th>
              <th className="px-4 py-3 font-medium text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-stone-100">
            {filtered.length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-10 text-center text-stone-500">
                  No returns in this filter.
                </td>
              </tr>
            )}
            {filtered.map((row) => (
              <QueueRow key={row.return_id ?? row.title} row={row} onRefresh={onRefresh} />
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}

function QueueRow({ row, onRefresh }: { row: WorkspaceQueueItem; onRefresh: () => void }) {
  const [open, setOpen] = useState(false)
  const stage = row.workflow_stage ?? 'investigate'
  const rid = row.return_id ?? row.title
  const prompt = analystAgentPrompt(stage, row.requested_resolution)

  return (
    <tr className="transition-colors hover:bg-stone-50/80">
      <td className="px-4 py-3">
        <p className="font-mono text-sm font-semibold text-stone-900">{rid}</p>
        <p className="mt-0.5 text-xs text-stone-500">{row.subtitle}</p>
        {row.case_id != null && (
          <p className="mt-0.5 text-xs text-stone-400">Case #{row.case_id}</p>
        )}
      </td>
      <td className="hidden px-4 py-3 text-stone-600 sm:table-cell">
        {humanize(row.requested_resolution ?? '')}
      </td>
      <td className="px-4 py-3">
        <Badge tone={stageTone(stage)}>{humanize(stage)}</Badge>
      </td>
      <td className="hidden max-w-xs px-4 py-3 text-stone-600 md:table-cell">{row.next_action}</td>
      <td className="px-4 py-3 text-right">
        <div className="flex flex-col items-end gap-1.5">
          <div className="flex flex-wrap justify-end gap-1.5">
            {stage === 'decline_request' && (
              <button type="button" className={button('secondary', 'sm')} onClick={() => setOpen((v) => !v)}>
                Decline
              </button>
            )}
            {stage === 'customer_follow_up' && row.notification_id != null && (
              <button type="button" className={button('secondary', 'sm')} onClick={() => setOpen((v) => !v)}>
                Review message
              </button>
            )}
            <AskAgentLink returnId={rid} draftMessage={prompt} />
          </div>
          <QueueUpdateHint row={row} />
          {row.warehouse_notes && stage === 'decline_request' && (
            <p className="max-w-xs text-right text-xs text-stone-500">Warehouse: {row.warehouse_notes}</p>
          )}
          {open && stage === 'decline_request' && (
            <DeclineForm returnId={rid} suggestedReason={row.warehouse_notes} onDone={() => { setOpen(false); onRefresh() }} />
          )}
          {open && stage === 'customer_follow_up' && row.notification_id != null && (
            <NotificationReview notificationId={row.notification_id} onDone={() => { setOpen(false); onRefresh() }} />
          )}
        </div>
      </td>
    </tr>
  )
}
