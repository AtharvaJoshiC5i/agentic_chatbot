import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import type { WorkspaceDashboardOut, WorkspaceQueueItem } from '../../api/types'
import { humanize } from '../../lib/format'
import { button } from '../ui/styles'
import { Badge } from '../ui/Badge'
import { VerdictForm } from './RowActions'

const STAGE_FILTERS: { id: string; label: string; match: (s: string) => boolean }[] = [
  { id: 'all', label: 'All', match: () => true },
  { id: 'receive', label: 'Receipt', match: (s) => s === 'receive' },
  { id: 'inspect', label: 'Inspection', match: (s) => s === 'inspect' },
  { id: 'verdict', label: 'Verdict', match: (s) => s === 'verdict' },
]

function stageTone(stage: string): 'accent' | 'warning' | 'neutral' {
  if (stage === 'receive') return 'warning'
  if (stage === 'inspect' || stage === 'verdict') return 'accent'
  return 'neutral'
}

function suggestedPrompt(row: WorkspaceQueueItem): string {
  const rid = row.return_id ?? ''
  const resolution = row.requested_resolution ?? 'refund or replacement'
  if (row.workflow_stage === 'receive') {
    return (
      `Use get_warehouse_handoff_status for ${rid} first. ` +
      `Analyst case #${row.case_id}; customer requested ${resolution}. ` +
      'There is no receipt or inspection recorded yet. Do not record receipt just because a case was opened. Ask whether the physical unit is present; only after explicit confirmation record receipt, then inspection. ' +
      'Do not say there is no open case. Do not approve refund or replacement.'
    )
  }
  if (row.workflow_stage === 'verdict') {
    return (
      `Use get_warehouse_handoff_status for ${rid}. Inspection is recorded. The customer requested ${resolution}. ` +
      'Tell me whether it can be performed (for a replacement, check stock), then record my verdict with record_warehouse_verdict. ' +
      'A decline needs a reason.'
    )
  }
  return (
    `Use get_warehouse_handoff_status for ${rid} first. ` +
    `Customer requested ${resolution}. Check the recorded receipt first; do not infer physical arrival from return status or case handoff. If not received, ask before recording receipt or inspection. ` +
    'Summarize handoff status and inspection findings for the analyst. Do not approve refund or replacement.'
  )
}

export function WarehouseWorkQueue({ data, onRefresh }: { data: WorkspaceDashboardOut; onRefresh: () => void }) {
  const [filter, setFilter] = useState('all')
  const items = data.sections.find((s) => s.key === 'warehouse_handoffs')?.items ?? []

  const filtered = useMemo(() => {
    const rule = STAGE_FILTERS.find((f) => f.id === filter) ?? STAGE_FILTERS[0]
    return items.filter((row) => rule.match(row.workflow_stage ?? ''))
  }, [filter, items])

  return (
    <section aria-labelledby="warehouse-queue-title">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 id="warehouse-queue-title" className="text-sm font-semibold text-stone-900">
            Analyst handoffs
          </h2>
          <p className="mt-0.5 text-xs text-stone-500">
            Receive and inspect — applies to both refund and replacement requests.
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
              <th className="hidden px-4 py-3 font-medium sm:table-cell">Customer ask</th>
              <th className="px-4 py-3 font-medium">Step</th>
              <th className="hidden px-4 py-3 font-medium md:table-cell">Next</th>
              <th className="px-4 py-3 font-medium text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-stone-100">
            {filtered.length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-12 text-center text-stone-500">
                  <p className="text-sm">No handoffs in this filter.</p>
                  <p className="mt-1 text-xs text-stone-400">
                    Returns appear here after an analyst opens an investigation case.
                  </p>
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
  const stage = row.workflow_stage ?? 'inspect'
  const rid = row.return_id ?? row.title

  return (
    <tr className="transition-colors hover:bg-stone-50/80">
      <td className="px-4 py-3">
        <p className="font-mono text-sm font-semibold text-stone-900">{rid}</p>
        <p className="mt-0.5 text-xs text-stone-500">{row.subtitle}</p>
      </td>
      <td className="hidden px-4 py-3 text-stone-600 sm:table-cell">
        {humanize(row.requested_resolution ?? '')}
      </td>
      <td className="px-4 py-3">
        <Badge tone={stageTone(stage)}>{humanize(stage)}</Badge>
      </td>
      <td className="hidden px-4 py-3 text-stone-600 md:table-cell">{row.next_action}</td>
      <td className="px-4 py-3 text-right">
        <div className="flex flex-col items-end gap-1.5">
          <div className="flex flex-wrap justify-end gap-1.5">
            {stage === 'verdict' && (
              <button type="button" className={button('secondary', 'sm')} onClick={() => setOpen((v) => !v)}>
                Give verdict
              </button>
            )}
            <Link
              to={`/workspace?return=${encodeURIComponent(rid)}`}
              state={{ draftMessage: suggestedPrompt(row) }}
              className={button('primary', 'sm')}
            >
              Open agent
            </Link>
          </div>
          {open && stage === 'verdict' && (
            <VerdictForm returnId={rid} resolution={row.requested_resolution ?? 'refund'} onDone={() => { setOpen(false); onRefresh() }} />
          )}
        </div>
      </td>
    </tr>
  )
}
