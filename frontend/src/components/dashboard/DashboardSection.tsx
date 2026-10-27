import type { ReactNode } from 'react'
import type { WorkspaceQueueItem } from '../../api/types'
import { analystAgentPrompt, genericAgentPrompt } from '../../lib/workflowAgent'
import { Badge } from '../ui/Badge'
import { formatDateTime, formatInrFromPaise, humanize } from '../../lib/format'
import { AskAgentLink } from './AskAgentLink'

function severityTone(severity: string | null | undefined): 'danger' | 'warning' | 'neutral' | 'accent' {
  if (severity === 'critical' || severity === 'high') return 'danger'
  if (severity === 'warning') return 'warning'
  if (severity === 'info') return 'neutral'
  return 'accent'
}

type RowExtras = {
  trailing?: ReactNode
}

function QueueRow({ item, extras }: { item: WorkspaceQueueItem; extras?: RowExtras }) {
  const rid = item.return_id
  const draft = rid
    ? item.workflow_stage
      ? analystAgentPrompt(item.workflow_stage, item.requested_resolution)
      : genericAgentPrompt(rid, item.workflow_stage)
    : ''

  return (
    <li className="flex flex-wrap items-center justify-between gap-3 px-4 py-3">
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          {item.severity && <Badge tone={severityTone(item.severity)}>{item.severity}</Badge>}
          {item.overdue && <Badge tone="danger">Overdue</Badge>}
          {item.priority && (
            <span className="text-xs font-medium text-stone-500">{humanize(item.priority)}</span>
          )}
          <p className="font-mono text-sm font-medium text-stone-900">{item.title}</p>
        </div>
        {item.subtitle && <p className="mt-0.5 text-sm text-stone-600">{item.subtitle}</p>}
        {item.due_date && (
          <time className="mt-0.5 block text-xs text-stone-400">
            Due {formatDateTime(item.due_date)}
          </time>
        )}
        {item.amount_paise != null && (
          <p className="mt-0.5 text-sm font-medium text-stone-800">
            {formatInrFromPaise(item.amount_paise)}
          </p>
        )}
      </div>
      <div className="flex shrink-0 flex-wrap items-center gap-2">
        {extras?.trailing}
        {rid && draft && <AskAgentLink returnId={rid} draftMessage={draft} variant="secondary" />}
      </div>
    </li>
  )
}

export function DashboardSection({
  title,
  items,
  emptyMessage,
  renderTrailing,
  headerAction,
}: {
  title: string
  items: WorkspaceQueueItem[]
  emptyMessage?: string
  renderTrailing?: (item: WorkspaceQueueItem) => ReactNode
  headerAction?: ReactNode
}) {
  return (
    <section>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-sm font-semibold text-stone-900">{title}</h2>
        {headerAction}
      </div>
      <ul className="mt-3 divide-y divide-stone-100 rounded-xl border border-stone-200 bg-white">
        {items.length === 0 && (
          <li className="px-4 py-6 text-sm text-stone-500">
            {emptyMessage ?? 'Nothing here right now.'}
          </li>
        )}
        {items.map((item, index) => (
          <QueueRow
            key={`${item.kind}-${item.case_id ?? item.action_id ?? item.refund_id ?? item.alert_id ?? item.recovery_task_id ?? index}`}
            item={item}
            extras={renderTrailing ? { trailing: renderTrailing(item) } : undefined}
          />
        ))}
      </ul>
    </section>
  )
}
