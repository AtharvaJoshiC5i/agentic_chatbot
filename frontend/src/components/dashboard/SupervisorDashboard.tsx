import type { WorkspaceDashboardOut } from '../../api/types'
import { RecentUpdatesStrip } from './RecentUpdatesStrip'
import { SupervisorApprovalsQueue } from './SupervisorApprovalsQueue'

export function SupervisorDashboard({
  data,
  onRefresh,
}: {
  data: WorkspaceDashboardOut
  onRefresh: () => void
}) {
  const recent = data.sections.find((s) => s.key === 'recent_updates')?.items ?? []

  return (
    <div className="space-y-8">
      <RecentUpdatesStrip items={recent} />
      <SupervisorApprovalsQueue data={data} onRefresh={onRefresh} />
    </div>
  )
}
