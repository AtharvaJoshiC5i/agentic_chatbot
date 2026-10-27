import type { WorkspaceQueueItem } from '../../api/types'
import { formatRelativeShort } from '../../lib/format'

export function QueueUpdateHint({ row }: { row: WorkspaceQueueItem }) {
  if (!row.handoff_from_other || !row.last_update_summary) return null
  return (
    <p className="mt-1 max-w-md text-left text-xs leading-relaxed text-accent-800/90 sm:text-right">
      {row.last_update_actor_label ? `${row.last_update_actor_label}: ` : 'Update: '}
      <span className="text-stone-600">{row.last_update_summary}</span>
      {row.last_activity_at && (
        <span className="ml-1 text-stone-400">· {formatRelativeShort(row.last_activity_at)}</span>
      )}
    </p>
  )
}
