import { useEffect, useState } from 'react'
import { api } from '../../api/client'
import type { CustomerNotificationOut } from '../../api/types'
import { useToast } from '../../context/ToastContext'
import { fieldInput } from '../ui/styles'
import { button } from '../ui/styles'

const textarea =
  'block w-full rounded-lg border border-stone-200 bg-white px-3 py-2 text-sm text-stone-900 placeholder:text-stone-400 focus:border-accent-500 focus:outline-none focus:ring-4 focus:ring-accent-500/15'

function errorText(e: unknown, fallback: string): string {
  return e instanceof Error ? e.message : fallback
}

/** Warehouse manager: can the customer's refund or replacement be performed? Goes back to the analyst. */
export function VerdictForm({ returnId, resolution, onDone }: { returnId: string; resolution: string; onDone: () => void }) {
  const { showToast } = useToast()
  const [notes, setNotes] = useState('')
  const [busy, setBusy] = useState(false)
  const label = resolution === 'replacement' ? 'replacement' : 'refund'

  async function submit(feasible: boolean) {
    if (!feasible && !notes.trim()) {
      showToast('Add the reason it cannot be performed.')
      return
    }
    setBusy(true)
    try {
      await api.recordVerdict(returnId, { feasible, recommendation: feasible ? 'proceed' : 'decline', notes: notes.trim() || undefined })
      showToast(`Verdict sent to the returns analyst for ${returnId}.`)
      onDone()
    } catch (e) {
      showToast(errorText(e, 'Could not record the verdict'))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="mt-2 w-72 space-y-2 text-left">
      <textarea
        className={textarea}
        rows={2}
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
        placeholder={`Notes for the analyst (required if the ${label} cannot be performed)`}
        aria-label="Verdict notes"
      />
      <div className="flex gap-1.5">
        <button type="button" className={button('primary', 'sm')} disabled={busy} onClick={() => void submit(true)}>
          Can be performed
        </button>
        <button type="button" className={button('secondary', 'sm')} disabled={busy} onClick={() => void submit(false)}>
          Cannot be performed
        </button>
      </div>
    </div>
  )
}

/** Analyst: decline the request (typically after a decline verdict). A customer message draft is created. */
export function DeclineForm({ returnId, suggestedReason, onDone }: { returnId: string; suggestedReason?: string | null; onDone: () => void }) {
  const { showToast } = useToast()
  const [reason, setReason] = useState(suggestedReason ?? '')
  const [busy, setBusy] = useState(false)

  async function submit() {
    if (!reason.trim()) {
      showToast('A reason is required to decline.')
      return
    }
    setBusy(true)
    try {
      await api.declineReturn(returnId, reason.trim())
      showToast(`Request declined. Review the customer message draft for ${returnId}.`)
      onDone()
    } catch (e) {
      showToast(errorText(e, 'Could not decline the request'))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="mt-2 w-72 space-y-2 text-left">
      <textarea className={textarea} rows={2} value={reason} onChange={(e) => setReason(e.target.value)} aria-label="Reason for declining" />
      <button type="button" className={button('secondary', 'sm')} disabled={busy} onClick={() => void submit()}>
        Decline and draft message
      </button>
    </div>
  )
}

/** Supervisor: a rejection needs a reason, which becomes part of the customer message draft. */
export function RejectReason({ onConfirm, onCancel, busy }: { onConfirm: (reason: string) => void; onCancel: () => void; busy: boolean }) {
  const [reason, setReason] = useState('')
  return (
    <div className="mt-2 w-64 space-y-2 text-left">
      <textarea className={textarea} rows={2} value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Reason (included in the analyst and customer message drafts)" aria-label="Rejection reason" autoFocus />
      <div className="flex gap-1.5">
        <button type="button" className={button('primary', 'sm')} disabled={busy || !reason.trim()} onClick={() => onConfirm(reason.trim())}>
          Confirm reject
        </button>
        <button type="button" className={button('ghost', 'sm')} onClick={onCancel}>
          Cancel
        </button>
      </div>
    </div>
  )
}

/** Analyst: review the drafted customer message, edit it if needed, and confirm it. This closes the case. */
export function NotificationReview({ notificationId, onDone }: { notificationId: number; onDone: () => void }) {
  const { showToast } = useToast()
  const [note, setNote] = useState<CustomerNotificationOut | null>(null)
  const [subject, setSubject] = useState('')
  const [body, setBody] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    let cancelled = false
    api
      .getNotification(notificationId)
      .then((n) => {
        if (cancelled) return
        setNote(n)
        setSubject(n.subject)
        setBody(n.body)
      })
      .catch((e) => showToast(errorText(e, 'Could not load the message draft')))
    return () => {
      cancelled = true
    }
  }, [notificationId, showToast])

  async function send() {
    setBusy(true)
    try {
      await api.sendNotification(notificationId, { subject, body })
      showToast('Message confirmation recorded. This demo did not send an email. The case and return are closed.')
      onDone()
    } catch (e) {
      showToast(errorText(e, 'Could not record message confirmation'))
    } finally {
      setBusy(false)
    }
  }

  if (!note) return <p className="mt-2 text-xs text-stone-500">Loading draft…</p>
  return (
    <div className="mt-2 w-80 space-y-2 text-left">
      <p className="text-xs text-stone-500">Draft addressed to {note.to_email}</p>
      <p className="rounded-md bg-amber-50 px-2 py-1.5 text-xs text-amber-900">Confirmation closes the case and return. This demo records the message locally and does not send email.</p>
      <input className={fieldInput} value={subject} onChange={(e) => setSubject(e.target.value)} aria-label="Email subject" />
      <textarea className={textarea} rows={7} value={body} onChange={(e) => setBody(e.target.value)} aria-label="Email body" />
      <button type="button" className={button('primary', 'sm')} disabled={busy} onClick={() => void send()}>
        Confirm message
      </button>
    </div>
  )
}
