import type { WorkspaceDashboardOut } from '../../api/types'
import { kpiLabel } from './dashboardKpiLabels'

export function DashboardKpiGrid({ data }: { data: WorkspaceDashboardOut }) {
  const entries = Object.entries(data.kpis)

  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
      {entries.map(([key, value]) => (
        <div
          key={key}
          className="rounded-xl border border-stone-200 bg-white px-4 py-3 shadow-sm"
        >
          <p className="text-xs font-medium uppercase tracking-wide text-stone-500">
            {kpiLabel(data.persona, key)}
          </p>
          <p className="mt-1 text-2xl font-semibold tabular-nums text-stone-900">{value}</p>
        </div>
      ))}
    </div>
  )
}
