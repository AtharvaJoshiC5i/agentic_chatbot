import { Loader2 } from 'lucide-react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import { AnalystDashboard } from '../components/dashboard/AnalystDashboard'
import { SupervisorDashboard } from '../components/dashboard/SupervisorDashboard'
import { WarehouseDashboard } from '../components/dashboard/WarehouseDashboard'
import { WorkflowGuide } from '../components/dashboard/WorkflowGuide'
import { WorkspaceNav } from '../components/layout/WorkspaceNav'
import { useAuth } from '../context/AuthContext'
import { useLiveResource } from '../hooks/useLiveResource'
import { showsSupervisorApprovalsNav } from '../lib/personaWorkspace'

export function DashboardPage() {
  const { role } = useAuth()
  const isAnalyst = Boolean(role?.includes('analyst') && !role?.includes('supervisor'))
  const isWarehouse = Boolean(role?.includes('warehouse'))
  const approvalsUi = showsSupervisorApprovalsNav(role)

  const { data, loading, error, refresh } = useLiveResource(() => api.workspaceDashboard(), [])
  const personaKey = data?.persona

  const heading =
    personaKey === 'returns_analyst'
      ? 'Returns queue'
      : personaKey === 'warehouse_manager'
        ? 'Inspection queue'
        : personaKey === 'returns_supervisor'
          ? 'Approvals queue'
          : isAnalyst
            ? 'Returns queue'
            : isWarehouse
              ? 'Inspection queue'
              : approvalsUi
                ? 'Approvals queue'
                : 'Queue'

  return (
    <div className="workspace-shell flex min-h-dvh flex-col">
      <WorkspaceNav />
      <div className="shrink-0 border-b border-stone-200 bg-white px-4 py-4 sm:px-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-lg font-semibold text-stone-900">{heading}</h1>
            <WorkflowGuide />
          </div>
          <Link to="/workspace" className="text-sm text-accent-700 underline-offset-2 hover:underline">
            Agent
          </Link>
        </div>
      </div>

      <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-6 sm:px-6">
        {error && (
          <p className="mb-4 rounded-lg border border-red-200 bg-red-50 px-3 py-2.5 text-sm text-red-700" role="alert">
            {error}
          </p>
        )}
        {loading && !data && (
          <div className="flex items-center gap-2 text-sm text-stone-500">
            <Loader2 className="size-4 animate-spin" aria-hidden />
            Loading…
          </div>
        )}
        {data && data.persona === 'returns_analyst' && <AnalystDashboard data={data} onRefresh={refresh} />}
        {data && data.persona === 'warehouse_manager' && <WarehouseDashboard data={data} onRefresh={refresh} />}
        {data && data.persona === 'returns_supervisor' && (
          <SupervisorDashboard data={data} onRefresh={refresh} />
        )}
      </main>
    </div>
  )
}
