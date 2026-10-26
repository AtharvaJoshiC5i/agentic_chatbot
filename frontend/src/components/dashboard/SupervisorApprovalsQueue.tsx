import { useCallback, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../api/client'
import type { WorkspaceDashboardOut, WorkspaceQueueItem } from '../../api/types'
import { useToast } from '../../context/ToastContext'
import { formatInrFromPaise, humanize } from '../../lib/format'
import { button } from '../ui/styles'
import { Badge } from '../ui/Badge'
import { RejectReason } from './RowActions'

const FILTERS = [
  { id: 'all', label: 'All', match: () => true },
  { id: 'refund', label: 'Refunds', match: (k: string) => k === 'refund' },
  { id: 'replacement', label: 'Replacements', match: (k: string) => k === 'replacement' },
] as const

function suggestedPrompt(row: WorkspaceQueueItem): string {
  const rid = row.return_id ?? ''
  const kind = row.approval_kind ?? row.action_type ?? 'request'
  return (
    `Use get_return_workflow_status for ${rid}. Review the analyst's pending ${kind} request ` +
    `(inspection on file: ${row.inspection_count ?? '—'}). ` +
    'Summarize risks and recommend approve or reject. If I approve in chat, use approve_action_request or approve_refund_request as appropriate.'
  )
}

export function SupervisorApprovalsQueue({
  data,
  onRefresh,
}: {
  data: WorkspaceDashboardOut
  onRefresh: () => void
}) {
  const { showToast } = useToast()
  const [filter, setFilter] = useState('all')
  const [busyId, setBusyId] = useState<string | null>(null)

  const items = data.sections.find((s) => s.key === 'approval_queue')?.items ?? []

  const filtered = useMemo(() => {
    const rule = FILTERS.find((f) => f.id === filter) ?? FILTERS[0]
    return items.filter((row) => rule.match((row.approval_kind ?? '').toLowerCase()))
  }, [filter, items])

  const actOnAction = useCallback(
    async (actionId: number, approve: boolean) => {
      setBusyId(`a-${actionId}`)
      try {
        await api.approveAction(actionId, approve)
        onRefresh()
      } catch (e) {
        showToast(e instanceof Error ? e.message : 'Approval failed')
      } finally {
        setBusyId(null)
      }
    },
    [onRefresh, showToast],
  )

  const actOnRefund = useCallback(
    async (refundId: number, approve: boolean, reason?: string) => {
      setBusyId(`r-${refundId}`)
      try {
        await api.approveRefund(refundId, approve, reason)
        onRefresh()
      } catch (e) {
        showToast(e instanceof Error ? e.message : 'Refund approval failed')
      } finally {
        setBusyId(null)
      }
    },
    [onRefresh, showToast],
  )

  const actOnReplacement = useCallback(
    async (replacementId: number, approve: boolean, reason?: string) => {
      setBusyId(`p-${replacementId}`)
      try {
        await api.decideReplacement(replacementId, approve, reason)
        onRefresh()
      } catch (e) {
        showToast(e instanceof Error ? e.message : 'Replacement decision failed')
      } finally {
        setBusyId(null)
      }
    },
    [onRefresh, showToast],
  )

  return (
    <section aria-labelledby="supervisor-queue-title">
      <div>
        <h2 id="supervisor-queue-title" className="text-sm font-semibold text-stone-900">
          Analyst submissions
        </h2>
        <p className="mt-0.5 text-xs text-stone-500">
          Approve or reject refund and replacement requests after warehouse inspection.
        </p>
      </div>

      <div className="mt-4 flex flex-wrap gap-1.5" role="tablist" aria-label="Filter approvals">
        {FILTERS.map((f) => (
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
              <th className="hidden px-4 py-3 font-medium sm:table-cell">Type</th>
              <th className="px-4 py-3 font-medium">Decision</th>
              <th className="hidden px-4 py-3 font-medium md:table-cell">Agent</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-stone-100">
            {filtered.length === 0 && (
              <tr>
                <td colSpan={4} className="px-4 py-12 text-center text-stone-500">
                  <p className="text-sm">No pending approvals.</p>
                  <p className="mt-1 text-xs text-stone-400">
                    Items appear when an analyst submits a refund or replacement request.
                  </p>
                </td>
              </tr>
            )}
            {filtered.map((row) => (
              <ApprovalRow
                key={`${row.return_id}-${row.refund_id ?? row.replacement_id ?? row.action_id}`}
                row={row}
                busyId={busyId}
                onRefund={actOnRefund}
                onAction={actOnAction}
                onReplacement={actOnReplacement}
              />
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}

function ApprovalRow({
  row,
  busyId,
  onRefund,
  onAction,
  onReplacement,
}: {
  row: WorkspaceQueueItem
  busyId: string | null
  onRefund: (id: number, approve: boolean, reason?: string) => void
  onAction: (id: number, approve: boolean) => void
  onReplacement: (id: number, approve: boolean, reason?: string) => void
}) {
  const [rejecting, setRejecting] = useState(false)
  const rid = row.return_id ?? row.title
  const kind = (row.approval_kind ?? 'request').toLowerCase()
  const prompt = suggestedPrompt(row)
  const verdict = typeof row.warehouse_verdict === 'object' ? row.warehouse_verdict : null

  const decide = (approve: boolean, reason?: string) => {
    if (row.refund_id != null) onRefund(row.refund_id, approve, reason)
    else if (row.replacement_id != null) onReplacement(row.replacement_id, approve, reason)
    else if (row.action_id != null) onAction(row.action_id, approve)
    setRejecting(false)
  }
  const needsReason = row.refund_id != null || row.replacement_id != null

  return (
    <tr className="hover:bg-stone-50/80 align-top">
      <td className="px-4 py-3">
        <p className="font-mono text-sm font-semibold text-stone-900">{rid}</p>
        <p className="mt-0.5 text-xs text-stone-500">{row.subtitle}</p>
        {row.inspection_count != null && row.inspection_count > 0 && (
          <p className="mt-0.5 text-xs text-emerald-700">Inspection on file</p>
        )}
        {verdict && (
          <p className="mt-0.5 text-xs text-stone-600">
            Warehouse verdict: {humanize(verdict.recommendation ?? '')}
            {verdict.notes ? ` — ${verdict.notes}` : ''}
          </p>
        )}
      </td>
      <td className="hidden px-4 py-3 sm:table-cell">
        <Badge tone={kind === 'refund' ? 'accent' : 'neutral'}>{humanize(kind)}</Badge>
        {row.amount_paise != null && (
          <p className="mt-1 text-xs text-stone-600">{formatInrFromPaise(row.amount_paise)}</p>
        )}
      </td>
      <td className="px-4 py-3">
        <div className="flex flex-wrap gap-1.5">
          <button type="button" className={button('primary', 'sm')} disabled={busyId !== null} onClick={() => decide(true)}>
            Approve
          </button>
          <button
            type="button"
            className={button('ghost', 'sm')}
            disabled={busyId !== null}
            onClick={() => (needsReason ? setRejecting((v) => !v) : decide(false))}
          >
            Reject
          </button>
        </div>
        {rejecting && needsReason && (
          <RejectReason busy={busyId !== null} onCancel={() => setRejecting(false)} onConfirm={(reason) => decide(false, reason)} />
        )}
      </td>
      <td className="hidden px-4 py-3 md:table-cell">
        <Link to={`/workspace?return=${encodeURIComponent(rid)}`} state={{ draftMessage: prompt }} className={button('secondary', 'sm')}>
          Ask agent
        </Link>
      </td>
    </tr>
  )
}
