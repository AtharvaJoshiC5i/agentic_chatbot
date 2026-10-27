import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import type { WorkspaceDashboardOut, WorkspaceQueueItem } from '../../api/types'
import { humanize } from '../../lib/format'
import { button } from '../ui/styles'
import { Badge } from '../ui/Badge'
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

function agentHref(returnId: string, stage: string | undefined): string {
  const base = `/workspace?return=${encodeURIComponent(returnId)}`
  if (stage === 'investigate') return `${base}&intent=investigate`
  if (stage === 'submit_refund') return `${base}&intent=refund`
  if (stage === 'submit_replacement') return `${base}&intent=replacement`
  if (stage === 'customer_follow_up') return `${base}&intent=customer`
  if (stage === 'await_warehouse') return `${base}&intent=warehouse`
  if (stage === 'decline_request') return `${base}&intent=decline`
  return base
}

function suggestedPrompt(stage: string | undefined, resolution: string | null | undefined): string {
  switch (stage) {
    case 'investigate':
      return (
        'Run the investigation and check the applicable company policy before any handoff. If a definite policy rule fails, explain the evidence and decline the return with the policy basis; do not send it to warehouse. If eligible, open a warehouse inspection case; if the data is incomplete or inconsistent, identify what is missing. Do not submit refund or replacement yet.'
      )
    case 'await_warehouse':
      return (
        'Call get_return_workflow_status for this return first. Say whether the warehouse has inspected the unit ' +
        'and given its verdict. I can only submit to the supervisor after a verdict that says proceed. ' +
        'Do not open a duplicate case.'
      )
    case 'decline_request':
      return (
        'Call get_return_workflow_status. The warehouse says this request cannot be performed. Summarise their ' +
        'reason, then ask me to confirm before using decline_return_request with that reason.'
      )
    case 'submit_refund':
      return (
        'Using inspection results and calculate_refundable_amount, submit a refund request for the ' +
        'remaining refundable amount if eligible. Do not approve payout yourself.'
      )
    case 'submit_replacement':
      return (
        'Using inspection results and return details, submit a replacement request for supervisor ' +
        'approval. Do not approve dispatch yourself.'
      )
    case 'await_supervisor':
      return `What is the status of my pending supervisor approval for this return (${resolution ?? 'refund or replacement'})?`
    case 'customer_follow_up':
      return (
        'Call list_customer_notifications for this return and show me the drafted customer email. ' +
        'After I confirm, record the message confirmation with send_customer_notification so the case closes. This demo does not deliver email.'
      )
    default:
      return 'Summarize this return and the next step in the analyst workflow.'
  }
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
            Investigate → open case → warehouse inspects → submit refund or replacement → confirm customer message.
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
  const prompt = suggestedPrompt(stage, row.requested_resolution)

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
            <Link to={agentHref(rid, stage)} state={{ draftMessage: prompt }} className={button('primary', 'sm')}>
              Open agent
            </Link>
          </div>
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
