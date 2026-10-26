import { Check, CircleSlash, Clock, ShieldAlert, X } from 'lucide-react'
import { useEffect, useState, type ReactNode } from 'react'
import { api } from '../../../api/client'
import { useAuth } from '../../../context/AuthContext'
import {
  formatInr,
  humanizeCode,
  type ActionsVisual,
  type CaseQueueVisual,
  type ChatVisual,
  type EvidenceVisual,
  type InvestigationVisual,
  type RecoveryVisual,
  type RefundLedgerVisual,
  type RefundQueueVisual,
  type ReturnWindowVisual,
  type WorkflowVisual,
} from '../../../lib/visuals'

type Tone = 'good' | 'warn' | 'bad' | 'neutral'

const TONES: Record<Tone, string> = {
  good: 'bg-emerald-50 text-emerald-700 ring-emerald-200',
  warn: 'bg-amber-50 text-amber-800 ring-amber-200',
  bad: 'bg-red-50 text-red-700 ring-red-200',
  neutral: 'bg-stone-100 text-stone-700 ring-stone-200',
}

function Badge({ tone = 'neutral', children }: { tone?: Tone; children: ReactNode }) {
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${TONES[tone]}`}>
      {children}
    </span>
  )
}

function Card({ title, meta, source, children }: { title: string; meta?: ReactNode; source: string; children: ReactNode }) {
  return (
    <section className="overflow-hidden rounded-md border border-stone-200 bg-white">
      <header className="flex items-center justify-between gap-3 border-b border-stone-100 px-4 py-3">
        <h3 className="text-sm font-semibold text-stone-900">{title}</h3>
        {meta}
      </header>
      <div className="px-4 py-3">{children}</div>
      <footer className="border-t border-stone-100 bg-stone-50/70 px-4 py-2 text-[11px] font-medium text-stone-500">
        Source: {source}
      </footer>
    </section>
  )
}

function checkTone(status: string): Tone {
  const s = status.toLowerCase()
  if (['pass', 'passed', 'ok', 'clear'].includes(s)) return 'good'
  if (['fail', 'failed', 'blocked'].includes(s)) return 'bad'
  if (['flag', 'flagged', 'warning', 'warn', 'review'].includes(s)) return 'warn'
  return 'neutral'
}

function outcomeTone(outcome: string): Tone {
  if (outcome.startsWith('eligible')) return 'good'
  if (outcome.includes('manual') || outcome.includes('exception') || outcome.includes('additional')) return 'warn'
  return 'neutral'
}

function Workflow({ v }: { v: WorkflowVisual }) {
  return (
    <Card
      title={`Workflow · ${v.return_id}`}
      meta={
        <Badge tone={v.warehouse_work_complete ? 'good' : 'warn'}>
          {v.warehouse_work_complete ? 'Warehouse complete' : 'Warehouse pending'}
        </Badge>
      }
      source={v.source}
    >
      <p className="text-sm text-stone-800">{v.status_summary}</p>
      <dl className="mt-3 grid gap-2 text-sm sm:grid-cols-2">
        <div>
          <dt className="text-xs text-stone-500">Analyst stage</dt>
          <dd className="font-medium text-stone-900">{humanizeCode(v.analyst_workflow_stage ?? '—')}</dd>
        </div>
        <div>
          <dt className="text-xs text-stone-500">Inspections on file</dt>
          <dd className="font-medium text-stone-900">{v.inspection_count}</dd>
        </div>
        {v.active_case && (
          <div className="sm:col-span-2">
            <dt className="text-xs text-stone-500">Investigation case</dt>
            <dd className="font-medium text-stone-900">
              Case #{v.active_case.case_id} · {humanizeCode(v.active_case.case_status)}
            </dd>
          </div>
        )}
      </dl>
    </Card>
  )
}

function Investigation({ v }: { v: InvestigationVisual }) {
  const flagged = v.checks.filter((c) => checkTone(c.status) !== 'good')
  const [showAll, setShowAll] = useState(false)
  const list = showAll ? v.checks : flagged.length ? flagged : v.checks.slice(0, 4)
  return (
    <Card title={`Investigation · ${v.return_id}`} meta={<Badge tone={outcomeTone(v.outcome)}>{humanizeCode(v.outcome)}</Badge>} source={v.source}>
      <dl className="grid gap-3 text-sm sm:grid-cols-2">
        <div>
          <dt className="text-xs text-stone-500">Signal</dt>
          <dd className="mt-0.5 font-medium text-stone-900">{humanizeCode(v.signal)}</dd>
        </div>
        <div>
          <dt className="text-xs text-stone-500">Recommended next step</dt>
          <dd className="mt-0.5 font-medium text-stone-900">{v.recommended_actions.map(humanizeCode).join(', ') || '—'}</dd>
        </div>
      </dl>
      <ul className="mt-3 divide-y divide-stone-100 rounded-lg border border-stone-100">
        {list.map((c) => (
          <li key={c.title} className="flex items-start justify-between gap-3 px-3 py-2 text-sm">
            <span className="min-w-0">
              <span className="font-medium text-stone-900">{c.title}</span>
              <span className="block text-xs leading-5 text-stone-600">{c.summary}</span>
            </span>
            <Badge tone={checkTone(c.status)}>{humanizeCode(c.status)}</Badge>
          </li>
        ))}
      </ul>
      {v.checks.length > list.length || showAll ? (
        <button type="button" onClick={() => setShowAll((s) => !s)} className="mt-2 text-xs font-medium text-accent-700 hover:underline">
          {showAll ? 'Show flagged checks only' : `Show all ${v.checks.length} checks`}
        </button>
      ) : null}
    </Card>
  )
}

function ReturnWindow({ v }: { v: ReturnWindowVisual }) {
  const days = v.days_after_delivery ?? 0
  const limit = v.window_days ?? 0
  const scale = Math.max(days, limit, 1) * 1.15
  const inside = v.within_window
  return (
    <Card
      title={`Return window · ${v.return_id}`}
      meta={inside == null ? <Badge>Not determined</Badge> : <Badge tone={inside ? 'good' : 'warn'}>{inside ? 'Inside window' : 'Outside window'}</Badge>}
      source={v.source}
    >
      <p className="text-sm text-stone-700">
        Requested <span className="font-semibold text-stone-900">{days} days</span> after delivery; the {humanizeCode(v.category).toLowerCase()} window is{' '}
        <span className="font-semibold text-stone-900">{limit} days</span>.
      </p>
      <div className="relative mt-3 h-3 rounded-full bg-stone-100" role="img" aria-label={`${days} of ${limit} days`}>
        <div className={`absolute inset-y-0 left-0 rounded-full ${inside ? 'bg-emerald-500' : 'bg-amber-500'}`} style={{ width: `${(days / scale) * 100}%` }} />
        <div className="absolute -inset-y-1 w-0.5 bg-stone-700" style={{ left: `${(limit / scale) * 100}%` }} />
      </div>
      <div className="mt-2 flex justify-between text-xs text-stone-500">
        <span>Delivered {v.delivered ?? '—'}</span>
        <span>Window ends day {limit}</span>
        <span>Requested {v.requested ?? '—'}</span>
      </div>
      {v.warranty_months != null && (
        <p className="mt-2 text-xs text-stone-600">
          Warranty: {v.warranty_months} months · {v.within_warranty ? 'still covered' : 'expired'}
        </p>
      )}
    </Card>
  )
}

function Evidence({ v }: { v: EvidenceVisual }) {
  const mismatch = v.inspections.some((i) => i.serial_match === false)
  const conflict = v.inspections.length > 1 && new Set(v.inspections.map((i) => i.defect_verified)).size > 1
  return (
    <Card
      title={`Evidence · ${v.return_id}`}
      meta={mismatch ? <Badge tone="warn">Serial mismatch</Badge> : conflict ? <Badge tone="warn">Inspections disagree</Badge> : v.inspections.length === 0 ? <Badge tone="warn">No inspection</Badge> : <Badge tone="good">Consistent</Badge>}
      source={v.source}
    >
      {v.inspections.length === 0 ? (
        <p className="text-sm text-stone-700">No inspection has been recorded for this return, so the evidence is insufficient for a decision.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="text-xs text-stone-500">
              <tr>
                <th className="py-1.5 pr-3 font-medium">Inspection</th>
                <th className="py-1.5 pr-3 font-medium">Serial (purchased {v.purchased_serial ?? 'n/a'})</th>
                <th className="py-1.5 pr-3 font-medium">Condition</th>
                <th className="py-1.5 pr-3 font-medium">Defect verified</th>
                <th className="py-1.5 font-medium">Result</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-stone-100">
              {v.inspections.map((i) => (
                <tr key={i.inspection_id}>
                  <td className="py-2 pr-3 text-stone-700">#{i.inspection_id} · {i.date}</td>
                  <td className={`py-2 pr-3 font-mono text-[13px] ${i.serial_match === false ? 'font-semibold text-red-700' : 'text-stone-800'}`}>
                    {i.returned_serial ?? '—'}
                  </td>
                  <td className="py-2 pr-3">
                    <Badge tone={i.condition === 'unsafe' ? 'bad' : ['damaged', 'defective'].includes(i.condition) ? 'warn' : 'neutral'}>{humanizeCode(i.condition)}</Badge>
                  </td>
                  <td className="py-2 pr-3 text-stone-800">{i.defect_verified ? 'Yes' : 'No'}</td>
                  <td className="py-2 text-stone-800">{humanizeCode(i.result)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  )
}

function Recovery({ v }: { v: RecoveryVisual }) {
  const max = Math.max(1, ...v.options.map((o) => Math.abs(o.net_inr)))
  return (
    <Card
      title={`Recovery options · ${v.return_id}`}
      meta={v.unsafe ? <Badge tone="bad"><ShieldAlert className="size-3.5" aria-hidden />Unsafe · no resale</Badge> : v.recommended_method ? <Badge tone="good">Best: {humanizeCode(v.recommended_method)}</Badge> : undefined}
      source={v.source}
    >
      <ul className="space-y-2.5">
        {v.options.map((o) => {
          const best = o.method === v.recommended_method && o.eligible
          const width = `${Math.max(4, (Math.abs(o.net_inr) / max) * 100)}%`
          return (
            <li key={o.method} className={o.eligible ? '' : 'opacity-60'}>
              <div className="flex items-center justify-between gap-3 text-sm">
                <span className={`font-medium ${best ? 'text-stone-900' : 'text-stone-700'}`}>
                  {humanizeCode(o.method)}
                  {best && <span className="ml-2 text-xs font-medium text-emerald-700">Recommended</span>}
                </span>
                <span className={`tabular-nums ${o.net_inr < 0 ? 'text-red-700' : 'text-stone-900'}`}>{formatInr(o.net_inr)}</span>
              </div>
              <div className="mt-1 h-2 rounded-full bg-stone-100">
                <div className={`h-2 rounded-full ${!o.eligible ? 'bg-stone-300' : o.net_inr < 0 ? 'bg-red-400' : best ? 'bg-emerald-500' : 'bg-accent-500'}`} style={{ width }} />
              </div>
              {!o.eligible && o.reason && (
                <p className="mt-1 flex items-center gap-1 text-xs text-stone-500">
                  <CircleSlash className="size-3" aria-hidden />
                  {o.reason}
                </p>
              )}
            </li>
          )
        })}
      </ul>
      {v.requires_approval && <p className="mt-3 text-xs text-amber-800">This recovery route requires supervisor approval.</p>}
    </Card>
  )
}

function RefundLedger({ v }: { v: RefundLedgerVisual }) {
  return (
    <Card
      title={`Refund ledger · ${v.return_id}`}
      meta={
        v.has_completed ? (
          <Badge tone="good">Payout completed</Badge>
        ) : (
          <Badge tone="warn">No completed payout yet</Badge>
        )
      }
      source={v.source}
    >
      {v.refunds.length === 0 ? (
        <p className="text-sm text-stone-700">No refund has been requested or issued for this return.</p>
      ) : (
        <ul className="divide-y divide-stone-100 text-sm">
          {v.refunds.map((r) => (
            <li key={r.refund_id} className="flex items-center justify-between gap-3 py-2">
              <span className="text-stone-700">Refund #{r.refund_id}{r.processed ? ` · processed ${r.processed}` : ''}</span>
              <span className="flex items-center gap-2">
                <span className="tabular-nums font-medium text-stone-900">{formatInr(r.amount_inr)}</span>
                <Badge tone={r.status === 'completed' ? 'good' : r.status === 'requested' ? 'warn' : 'neutral'}>{humanizeCode(r.status)}</Badge>
              </span>
            </li>
          ))}
        </ul>
      )}
      <p className="mt-2 text-xs text-stone-500">
        Customer payout is tracked here. <strong className="font-medium text-stone-700">Actions</strong> above
        are the approval queue; status must be <strong className="font-medium text-stone-700">completed</strong>{' '}
        before telling the customer money was sent.
      </p>
      {v.has_completed && (
        <p className="mt-1 text-xs text-stone-600">
          Only one completed refund is allowed per return; further refund requests are blocked.
        </p>
      )}
    </Card>
  )
}

const APPROVER_ROLES = new Set(['returns_supervisor', 'administrator'])

type ActionLiveRow = { approval: string; execution: string; error?: string; busy?: boolean }

function mergeActionsVisual(v: ActionsVisual, live: Record<number, ActionLiveRow>): ActionsVisual {
  return {
    ...v,
    actions: v.actions.map((a) => ({
      ...a,
      approval: live[a.action_id]?.approval ?? a.approval,
      execution: live[a.action_id]?.execution ?? a.execution,
    })),
  }
}

function Actions({
  v,
  onVisualUpdate,
}: {
  v: ActionsVisual
  onVisualUpdate?: (next: ActionsVisual) => void
}) {
  const { role } = useAuth()
  const canApprove = role != null && APPROVER_ROLES.has(role)
  const [live, setLive] = useState<Record<number, ActionLiveRow>>({})
  const actionIdsKey = v.actions.map((a) => a.action_id).join(',')

  function patchLive(actionId: number, patch: Partial<ActionLiveRow>) {
    setLive((prev) => {
      const base = prev[actionId]
      const row = v.actions.find((a) => a.action_id === actionId)
      const next = {
        ...prev,
        [actionId]: {
          approval: patch.approval ?? base?.approval ?? row?.approval ?? 'pending',
          execution: patch.execution ?? base?.execution ?? row?.execution ?? 'pending',
          error: patch.error,
          busy: patch.busy,
        },
      }
      onVisualUpdate?.(mergeActionsVisual(v, next))
      return next
    })
  }

  useEffect(() => {
    let cancelled = false
    async function refresh() {
      try {
        const res = await api.listActions(v.return_id, 100)
        if (cancelled) return
        const next: Record<number, ActionLiveRow> = {}
        for (const a of v.actions) {
          const found = res.items.find((i) => i.action_id === a.action_id)
          if (found) {
            next[a.action_id] = {
              approval: found.approval_status,
              execution: found.execution_status,
            }
          }
        }
        if (Object.keys(next).length > 0) {
          setLive((prev) => {
            const merged = { ...prev, ...next }
            onVisualUpdate?.(mergeActionsVisual(v, merged))
            return merged
          })
        }
      } catch {
        /* keep snapshot */
      }
    }
    void refresh()
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- refresh when return or action ids change
  }, [v.return_id, actionIdsKey])

  async function runExecute(actionId: number) {
    patchLive(actionId, { busy: true, error: undefined })
    try {
      const res = await api.executeAction(actionId)
      patchLive(actionId, {
        approval: res.approval_status,
        execution: res.execution_status,
        busy: false,
        error: undefined,
      })
    } catch (e) {
      patchLive(actionId, { busy: false, error: e instanceof Error ? e.message : 'Execute failed' })
    }
  }

  async function approve(actionId: number) {
    patchLive(actionId, { busy: true, error: undefined })
    try {
      const res = await api.approveAction(actionId)
      patchLive(actionId, {
        approval: res.approval_status,
        execution: res.execution_status,
        busy: false,
        error: undefined,
      })
    } catch (e) {
      const message = e instanceof Error ? e.message : 'Approval failed'
      try {
        const fresh = await api.getAction(actionId)
        patchLive(actionId, {
          approval: fresh.approval_status,
          execution: fresh.execution_status,
          busy: false,
          error: fresh.approval_status === 'pending' ? message : undefined,
        })
      } catch {
        patchLive(actionId, { busy: false, error: message })
      }
    }
  }

  const display = mergeActionsVisual(v, live)

  return (
    <Card title={`Actions · ${v.return_id}`} source={v.source}>
      <ul className="divide-y divide-stone-100 text-sm">
        {display.actions.map((a) => {
          const local = live[a.action_id]
          const approval = a.approval
          const pending = approval === 'pending'
          return (
            <li key={a.action_id} className="flex flex-wrap items-center justify-between gap-2 py-2">
              <span className="min-w-0">
                <span className="font-medium text-stone-900">{humanizeCode(a.action_type)}</span>
                <span className="block text-xs text-stone-500">
                  #{a.action_id} · requested by {a.requested_by} · {humanizeCode(a.execution)}
                </span>
                {local?.error && <span className="block text-xs text-red-700">{local.error}</span>}
              </span>
              <span className="flex items-center gap-2">
                <Badge tone={approval === 'approved' || approval === 'not_required' ? 'good' : approval === 'rejected' ? 'bad' : 'warn'}>
                  {pending ? <Clock className="size-3.5" aria-hidden /> : approval === 'rejected' ? <X className="size-3.5" aria-hidden /> : <Check className="size-3.5" aria-hidden />}
                  {humanizeCode(approval === 'pending' ? 'pending_approval' : approval)}
                </Badge>
                {pending && canApprove && (
                  <button
                    type="button"
                    disabled={local?.busy}
                    onClick={() => void approve(a.action_id)}
                    className="h-8 rounded-lg bg-accent-600 px-3 text-xs font-medium text-white hover:bg-accent-700 disabled:opacity-50"
                  >
                    {local?.busy ? 'Approving…' : 'Approve'}
                  </button>
                )}
                {canApprove &&
                  a.action_type === 'request_refund' &&
                  (approval === 'approved' || approval === 'not_required') &&
                  a.execution !== 'succeeded' && (
                    <button
                      type="button"
                      disabled={local?.busy}
                      onClick={() => void runExecute(a.action_id)}
                      className="h-8 rounded-lg border border-stone-300 bg-white px-3 text-xs font-medium text-stone-800 hover:bg-stone-50 disabled:opacity-50"
                    >
                      {local?.busy ? 'Executing…' : 'Execute payout'}
                    </button>
                  )}
              </span>
            </li>
          )
        })}
      </ul>
      <p className="mt-2 text-xs text-stone-500">
        For refunds: approve the request, then <strong className="font-medium text-stone-700">Execute payout</strong>{' '}
        to record and complete the customer refund.
      </p>
      {!canApprove && display.actions.some((a) => a.approval === 'pending') && (
        <p className="mt-1 text-xs text-stone-500">A returns supervisor or administrator must approve pending actions.</p>
      )}
    </Card>
  )
}

function RefundQueue({ v }: { v: RefundQueueVisual }) {
  const tier = (amount: number) => (amount > v.thresholds_inr.supervisor ? 'Supervisor + finance' : amount > v.thresholds_inr.analyst ? 'Supervisor' : 'Analyst')
  return (
    <Card title="Refunds awaiting approval" meta={<Badge tone="warn">{v.count} pending · {formatInr(v.total_inr)}</Badge>} source={v.source}>
      <table className="w-full text-left text-sm">
        <thead className="text-xs text-stone-500">
          <tr>
            <th className="py-1.5 pr-3 font-medium">Return</th>
            <th className="py-1.5 pr-3 text-right font-medium">Amount</th>
            <th className="py-1.5 font-medium">Approval tier</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-stone-100">
          {v.rows.map((r) => (
            <tr key={r.refund_id}>
              <td className="py-2 pr-3 font-mono text-[13px] text-stone-900">{r.return_id}</td>
              <td className="py-2 pr-3 text-right tabular-nums text-stone-900">{formatInr(r.amount_inr)}</td>
              <td className="py-2 text-stone-700">{tier(r.amount_inr)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {v.count > v.rows.length && <p className="mt-2 text-xs text-stone-500">Showing the {v.rows.length} largest of {v.count}.</p>}
    </Card>
  )
}

function CaseQueue({ v }: { v: CaseQueueVisual }) {
  return (
    <Card title="Open investigation cases" meta={<Badge tone={v.overdue ? 'warn' : 'good'}>{v.overdue} overdue of {v.count}</Badge>} source={v.source}>
      <table className="w-full text-left text-sm">
        <thead className="text-xs text-stone-500">
          <tr>
            <th className="py-1.5 pr-3 font-medium">Case</th>
            <th className="py-1.5 pr-3 font-medium">Issue</th>
            <th className="py-1.5 pr-3 font-medium">Priority</th>
            <th className="py-1.5 pr-3 font-medium">Assignee</th>
            <th className="py-1.5 font-medium">Due</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-stone-100">
          {v.rows.map((c) => (
            <tr key={c.case_id}>
              <td className="py-2 pr-3 text-stone-900">#{c.case_id} <span className="font-mono text-[13px] text-stone-600">{c.return_id}</span></td>
              <td className="py-2 pr-3 text-stone-700">{humanizeCode(c.issue_type)}</td>
              <td className="py-2 pr-3"><Badge tone={c.priority === 'critical' ? 'bad' : c.priority === 'high' ? 'warn' : 'neutral'}>{humanizeCode(c.priority)}</Badge></td>
              <td className="py-2 pr-3 text-stone-700">{c.assigned_to ?? 'Unassigned'}</td>
              <td className={`py-2 tabular-nums ${c.overdue ? 'font-medium text-red-700' : 'text-stone-700'}`}>{c.due ?? '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </Card>
  )
}

export function ChatVisuals({
  visuals,
  onVisualAtIndex,
}: {
  visuals: ChatVisual[]
  onVisualAtIndex?: (index: number, next: ChatVisual) => void
}) {
  return (
    <div className="mt-4 space-y-3">
      {visuals.map((v, i) => {
        const key = `${v.type}-${'return_id' in v ? v.return_id : i}`
        switch (v.type) {
          case 'investigation':
            return <Investigation key={key} v={v} />
          case 'return_window':
            return <ReturnWindow key={key} v={v} />
          case 'workflow':
            return <Workflow key={key} v={v} />
          case 'evidence':
            return <Evidence key={key} v={v} />
          case 'recovery':
            return <Recovery key={key} v={v} />
          case 'refund_ledger':
            return <RefundLedger key={key} v={v} />
          case 'actions':
            return (
              <Actions
                key={key}
                v={v}
                onVisualUpdate={onVisualAtIndex ? (next) => onVisualAtIndex(i, next) : undefined}
              />
            )
          case 'refund_queue':
            return <RefundQueue key={key} v={v} />
          case 'case_queue':
            return <CaseQueue key={key} v={v} />
          default:
            return null
        }
      })}
    </div>
  )
}
