import type { WorkspaceQueueItem } from '../../api/types'
import { formatRelativeShort, humanize } from '../../lib/format'
import { analystAgentPrompt, genericAgentPrompt } from '../../lib/workflowAgent'
import { AskAgentLink } from './AskAgentLink'

function promptForRow(row: WorkspaceQueueItem): string {
  const rid = row.return_id ?? row.title
  if (row.last_update_summary && row.handoff_from_other) {
    return `Summarize the latest update for ${rid} and what I should do next in the returns workflow. Latest: ${row.last_update_summary}`
  }
  if (row.workflow_stage) {
    return analystAgentPrompt(row.workflow_stage, row.requested_resolution)
  }
  return genericAgentPrompt(rid, row.workflow_stage)
}

function stageLabel(row: WorkspaceQueueItem): string {
  if (row.workflow_stage) return humanize(row.workflow_stage)
  if (row.approval_kind) return humanize(row.approval_kind)
  return row.subtitle ?? ''
}

export function RecentUpdatesStrip({ items }: { items: WorkspaceQueueItem[] }) {
  if (items.length === 0) return null

  return (
    <section aria-labelledby="recent-updates-title" className="mb-6">
      <h2 id="recent-updates-title" className="text-sm font-semibold text-stone-900">
        Latest updates
      </h2>
      <p className="mt-0.5 text-xs text-stone-500">Recent actions from other roles on returns in your queue.</p>
      <ul className="mt-3 divide-y divide-stone-100 overflow-hidden rounded-xl border border-accent-200/80 bg-accent-50/30">
        {items.map((row) => {
          const rid = row.return_id ?? row.title
          return (
            <li key={rid} className="flex flex-wrap items-start justify-between gap-3 px-4 py-3">
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-mono text-sm font-semibold text-stone-900">{rid}</span>
                  {row.last_activity_at && (
                    <time className="text-[10px] tabular-nums text-stone-500">
                      {formatRelativeShort(row.last_activity_at)}
                    </time>
                  )}
                </div>
                <p className="mt-1 text-sm leading-relaxed text-stone-700">
                  {row.last_update_actor_label && (
                    <span className="font-medium text-accent-800">{row.last_update_actor_label}: </span>
                  )}
                  {row.last_update_summary ?? row.status_summary ?? row.subtitle}
                </p>
                {row.workflow_stage && (
                  <p className="mt-0.5 text-xs text-stone-500">{stageLabel(row)}</p>
                )}
              </div>
              <AskAgentLink returnId={rid} draftMessage={promptForRow(row)} variant="secondary" />
            </li>
          )
        })}
      </ul>
    </section>
  )
}
