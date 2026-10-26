import type { WorkspaceDashboardOut } from '../../api/types'
import { DashboardKpiGrid } from './DashboardKpiGrid'
import { WarehouseWorkQueue } from './WarehouseWorkQueue'

export function WarehouseDashboard({ data, onRefresh }: { data: WorkspaceDashboardOut; onRefresh: () => void }) {
  return (
    <div className="space-y-8">
      <DashboardKpiGrid data={data} />
      <WarehouseWorkQueue data={data} onRefresh={onRefresh} />
    </div>
  )
}
