import type { WorkspaceDashboardOut } from '../../api/types'
import { DashboardKpiGrid } from './DashboardKpiGrid'
import { SupervisorApprovalsQueue } from './SupervisorApprovalsQueue'

export function SupervisorDashboard({
  data,
  onRefresh,
}: {
  data: WorkspaceDashboardOut
  onRefresh: () => void
}) {
  return (
    <div className="space-y-8">
      <DashboardKpiGrid data={data} />
      <SupervisorApprovalsQueue data={data} onRefresh={onRefresh} />
    </div>
  )
}
