import type { WorkspaceDashboardOut } from '../../api/types'
import { DashboardSection } from './DashboardSection'
import { AnalystWorkQueue } from './AnalystWorkQueue'
import { RecentUpdatesStrip } from './RecentUpdatesStrip'

export function AnalystDashboard({ data, onRefresh }: { data: WorkspaceDashboardOut; onRefresh: () => void }) {
  const pending = data.sections.find((s) => s.key === 'my_pending_requests')
  const recent = data.sections.find((s) => s.key === 'recent_updates')?.items ?? []

  return (
    <div className="space-y-8">
      <RecentUpdatesStrip items={recent} />
      <AnalystWorkQueue data={data} onRefresh={onRefresh} />
      {pending && pending.items.length > 0 && (
        <DashboardSection
          title={pending.title}
          items={pending.items}
          emptyMessage="No pending submissions."
        />
      )}
    </div>
  )
}
