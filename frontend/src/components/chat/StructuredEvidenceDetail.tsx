import type { StructuredEvidence } from '../../api/types'
import { humanize } from '../../lib/format'

function tryParseJson(value: string): unknown | null {
  const t = value.trim()
  if (!t || (t[0] !== '[' && t[0] !== '{')) return null
  try {
    return JSON.parse(t) as unknown
  } catch {
    return null
  }
}

function formatScalar(value: string): string {
  const t = value.trim()
  if (!t) return '—'
  if (/^\d{4}-\d{2}-\d{2}T/.test(t)) {
    const d = new Date(t)
    if (!Number.isNaN(d.getTime())) {
      return d.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
    }
  }
  return t
}

function StatusBadge({ status }: { status: string }) {
  const normalized = status.toLowerCase()
  const tone =
    normalized === 'sent' || normalized === 'approved' || normalized === 'completed'
      ? 'bg-emerald-50 text-emerald-800 ring-emerald-200'
      : normalized === 'draft' || normalized === 'pending'
        ? 'bg-amber-50 text-amber-900 ring-amber-200'
        : 'bg-stone-100 text-stone-700 ring-stone-200'
  return (
    <span className={`inline-flex rounded-full px-2.5 py-0.5 text-[11px] font-semibold ring-1 ${tone}`}>
      {humanize(status)}
    </span>
  )
}

function NotificationCard({ row }: { row: Record<string, string> }) {
  const body = row.body?.replace(/\\n/g, '\n') ?? ''

  return (
    <article className="rounded-lg border border-stone-200 bg-white shadow-sm">
      <header className="border-b border-stone-100 px-4 py-3 sm:px-5">
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div className="min-w-0">
            <p className="text-sm font-semibold text-stone-900">{row.subject || 'Notification'}</p>
            <p className="mt-1 text-xs text-stone-500">
              To <span className="font-medium text-stone-700">{row.to_email || '—'}</span>
            </p>
          </div>
          {row.status && <StatusBadge status={row.status} />}
        </div>
      </header>
      <dl className="grid gap-0 divide-y divide-stone-100 px-4 sm:px-5">
        {row.return_id && (
          <div className="grid gap-1 py-3 sm:grid-cols-[140px_1fr]">
            <dt className="text-xs font-medium text-stone-500">Return</dt>
            <dd className="font-mono text-sm text-stone-900">{row.return_id}</dd>
          </div>
        )}
        {row.kind && (
          <div className="grid gap-1 py-3 sm:grid-cols-[140px_1fr]">
            <dt className="text-xs font-medium text-stone-500">Kind</dt>
            <dd className="text-sm text-stone-900">{humanize(row.kind)}</dd>
          </div>
        )}
        {body && (
          <div className="py-3">
            <dt className="text-xs font-medium text-stone-500">Message</dt>
            <dd className="mt-2 whitespace-pre-wrap rounded-md border border-stone-100 bg-stone-50/80 px-3 py-3 text-sm leading-relaxed text-stone-800">
              {body}
            </dd>
          </div>
        )}
      </dl>
      <footer className="flex flex-wrap gap-x-4 gap-y-1 border-t border-stone-100 px-4 py-2.5 text-[11px] text-stone-500 sm:px-5">
        {row.notification_id && <span>ID {row.notification_id}</span>}
        {row.created_by && <span>Created by {row.created_by}</span>}
        {row.created_at && <span>{formatScalar(row.created_at)}</span>}
      </footer>
    </article>
  )
}

function isNotificationRow(row: Record<string, string>): boolean {
  return Boolean(row.subject || row.to_email) && Boolean(row.notification_id || row.kind)
}

function FieldRow({ label, value }: { label: string; value: string }) {
  const parsed = tryParseJson(value)
  if (parsed && Array.isArray(parsed) && parsed.every((x) => x && typeof x === 'object')) {
    return (
      <div className="py-4">
        <h3 className="text-xs font-semibold uppercase tracking-wide text-stone-500">{label}</h3>
        <div className="mt-3 space-y-3">
          {(parsed as Record<string, unknown>[]).map((entry, i) => (
            <NotificationCard
              key={String(entry.notification_id ?? i)}
              row={Object.fromEntries(Object.entries(entry).map(([k, v]) => [k, String(v ?? '')]))}
            />
          ))}
        </div>
      </div>
    )
  }

  if (label.toLowerCase() === 'status') {
    return (
      <div className="grid gap-1 py-3 sm:grid-cols-[minmax(0,32%)_1fr] sm:gap-4">
        <dt className="text-xs font-medium text-stone-500">{label}</dt>
        <dd><StatusBadge status={value} /></dd>
      </div>
    )
  }

  if (label.toLowerCase() === 'body' || value.includes('\\n')) {
    const body = value.replace(/\\n/g, '\n')
    return (
      <div className="py-3">
        <dt className="text-xs font-medium text-stone-500">{label}</dt>
        <dd className="mt-2 whitespace-pre-wrap rounded-md border border-stone-100 bg-stone-50/80 px-3 py-3 text-sm leading-relaxed text-stone-800">
          {body}
        </dd>
      </div>
    )
  }

  return (
    <div className="grid gap-1 py-3 sm:grid-cols-[minmax(0,32%)_1fr] sm:gap-4">
      <dt className="text-xs font-medium text-stone-500">{label}</dt>
      <dd className="whitespace-pre-wrap break-words text-sm text-stone-900">{formatScalar(value)}</dd>
    </div>
  )
}

function RecordCard({ row, columns }: { row: Record<string, string>; columns: string[] }) {
  const cols = columns.length ? columns : Object.keys(row)
  const hiddenWhenNotification = new Set(['notifications', 'count'])

  if (isNotificationRow(row)) {
    return <NotificationCard row={row} />
  }

  const visible = cols.filter((col) => {
    if (hiddenWhenNotification.has(col) && cols.includes('notifications')) return false
    const v = row[col]
    return v != null && String(v).trim() !== ''
  })

  return (
    <article className="rounded-lg border border-stone-200 bg-white shadow-sm">
      <dl className="divide-y divide-stone-100 px-4 sm:px-5">
        {visible.map((col) => (
          <FieldRow key={col} label={humanize(col)} value={String(row[col] ?? '')} />
        ))}
      </dl>
    </article>
  )
}

export function StructuredEvidenceDetail({ item }: { item: StructuredEvidence }) {
  const rows = item.rows.length ? item.rows : [{}]
  const columns = item.columns.length ? item.columns : Object.keys(rows[0] ?? {})

  const allNotifications = rows.length > 0 && rows.every(isNotificationRow)

  return (
    <div className="min-h-0 flex-1 overflow-y-auto bg-stone-50/60 px-4 py-4 sm:px-5 sm:py-5">
      {allNotifications ? (
        <div className="mx-auto flex max-w-2xl flex-col gap-4">
          {rows.map((row, index) => (
            <NotificationCard key={row.notification_id ?? index} row={row} />
          ))}
        </div>
      ) : (
        <div className="mx-auto flex max-w-2xl flex-col gap-4">
          {rows.map((row, index) => (
            <RecordCard key={index} row={row} columns={columns} />
          ))}
        </div>
      )}
    </div>
  )
}
