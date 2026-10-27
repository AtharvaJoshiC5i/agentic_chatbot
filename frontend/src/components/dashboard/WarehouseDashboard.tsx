import type { WorkspaceDashboardOut } from '../../api/types'
import { RecentUpdatesStrip } from './RecentUpdatesStrip'
import { WarehouseWorkQueue } from './WarehouseWorkQueue'

export function WarehouseDashboard({ data, onRefresh }: { data: WorkspaceDashboardOut; onRefresh: () => void }) {
  const recent = data.sections.find((s) => s.key === 'recent_updates')?.items ?? []

  return (
    <div className="space-y-8">
      <RecentUpdatesStrip items={recent} />
      <WarehouseWorkQueue data={data} onRefresh={onRefresh} />
    </div>
  )
}
