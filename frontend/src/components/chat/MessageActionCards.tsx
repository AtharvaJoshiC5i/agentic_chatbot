import { useEffect, useState } from 'react'
import { useLiveResource } from '../../hooks/useLiveResource'
import { api } from '../../api/client'
import type { ActionOut } from '../../api/types'
import type { ToolEvent } from '../../lib/chats'
import { Badge } from '../ui/Badge'
import { button } from '../ui/styles'
import { formatInrFromPaise } from '../../lib/format'
import { useAuth } from '../../context/AuthContext'

function parseActionId(preview: string | undefined): number | null {
  if (!preview) return null
  const m = preview.match(/action_id["\s:]+(\d+)/i) ?? preview.match(/"id"\s*:\s*(\d+)/)
  return m ? Number(m[1]) : null
}

function statusBadge(action: ActionOut) {
  if (action.execution_status === 'succeeded') return <Badge tone="success">Executed</Badge>
  if (action.approval_status === 'rejected') return <Badge tone="danger">Rejected</Badge>
  if (action.approval_required && action.approval_status === 'pending') {
    return <Badge tone="warning">Pending approval</Badge>
  }
  if (action.approval_status === 'approved') return <Badge tone="accent">Approved</Badge>
  return <Badge tone="neutral">{action.execution_status}</Badge>
}

function ActionCard({ actionId, returnId }: { actionId: number; returnId?: string }) {
  const { role } = useAuth()
  const [action, setAction] = useState<ActionOut | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const canApprove = role?.includes('supervisor')

  const { data: liveAction, refresh } = useLiveResource(
    () =>
      api.getAction(actionId).catch(() => {
        if (!returnId) throw new Error('missing')
        return api.listActions(returnId, 50).then((res) => {
          const found = res.items.find((a) => a.action_id === actionId)
          if (!found) throw new Error('not found')
          return found
        })
      }),
    [actionId, returnId],
  )

  useEffect(() => {
    if (liveAction) setAction(liveAction)
  }, [liveAction])

  async function approve(approve: boolean) {
    setBusy(true)
    setError(null)
    try {
      const updated = await api.approveAction(actionId, approve)
      setAction(updated)
      refresh()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Approval failed')
    } finally {
      setBusy(false)
    }
  }

  async function execute() {
    setBusy(true)
    setError(null)
    try {
      const updated = await api.executeAction(actionId)
      setAction(updated)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Execute failed')
    } finally {
      setBusy(false)
    }
  }

  const label = action?.action_type?.replace(/_/g, ' ') ?? 'Action request'
  const amount =
    action?.payload && typeof action.payload === 'object' && 'refund_amount_paise' in action.payload
      ? formatInrFromPaise(Number((action.payload as { refund_amount_paise: number }).refund_amount_paise))
      : null

  return (
    <div className="mt-4 rounded-xl border border-stone-200 bg-stone-50 p-4">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <p className="text-sm font-semibold text-stone-900">{label}</p>
          <p className="mt-0.5 text-xs text-stone-600">
            Request #{actionId}
            {returnId ? ` · ${returnId}` : ''}
            {amount ? ` · ${amount}` : ''}
          </p>
        </div>
        {action ? statusBadge(action) : <Badge tone="neutral">Loading…</Badge>}
      </div>
      {error && <p className="mt-2 text-xs text-red-700">{error}</p>}
      {action && canApprove && action.approval_status === 'pending' && (
        <div className="mt-3 flex flex-wrap gap-2">
          <button type="button" className={button('primary', 'sm')} disabled={busy} onClick={() => approve(true)}>
            Approve
          </button>
          <button type="button" className={button('secondary', 'sm')} disabled={busy} onClick={() => approve(false)}>
            Reject
          </button>
        </div>
      )}
      {action &&
        canApprove &&
        action.approval_status === 'approved' &&
        action.execution_status !== 'succeeded' && (
          <button type="button" className={`${button('primary', 'sm')} mt-3`} disabled={busy} onClick={() => execute()}>
            Execute payout
          </button>
        )}
      {action?.action_type === 'request_refund' && action.approval_status === 'pending' && (
        <p className="mt-2 text-xs text-stone-500">
          Supervisor approval completes payout automatically when within policy limits.
        </p>
      )}
    </div>
  )
}

export function MessageActionCards({
  toolEvents,
  returnId,
}: {
  toolEvents?: ToolEvent[]
  returnId?: string | null
}) {
  if (!toolEvents?.length) return null
  const cards: { id: number; returnId?: string }[] = []
  for (const ev of toolEvents) {
    if (!ev.tool?.startsWith('submit_')) continue
    const id = parseActionId(ev.result_preview)
    if (!id) continue
    const fromArgs =
      typeof ev.args?.return_id === 'string' ? ev.args.return_id : undefined
    cards.push({ id, returnId: returnId ?? fromArgs })
  }
  if (!cards.length) return null
  return (
    <>
      {cards.map(({ id, returnId: rid }) => (
        <ActionCard key={id} actionId={id} returnId={rid} />
      ))}
    </>
  )
}
