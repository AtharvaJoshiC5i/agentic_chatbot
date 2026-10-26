import { LayoutDashboard, Loader2, RefreshCw } from 'lucide-react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import { AnalystDashboard } from '../components/dashboard/AnalystDashboard'
import { SupervisorDashboard } from '../components/dashboard/SupervisorDashboard'
import { WarehouseDashboard } from '../components/dashboard/WarehouseDashboard'
import { WorkspaceNav } from '../components/layout/WorkspaceNav'
import { useAuth } from '../context/AuthContext'
import { useLiveResource } from '../hooks/useLiveResource'
import { showsSupervisorApprovalsNav, workspacePersonaForRole } from '../lib/personaWorkspace'
import { button, panelTitle } from '../components/ui/styles'

export function DashboardPage() {
  const { role } = useAuth()
  const persona = workspacePersonaForRole(role)
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
                : 'Dashboard'

  const blurb =
    personaKey === 'returns_analyst' || (isAnalyst && !personaKey)
      ? 'Triage returns, coordinate warehouse inspection, and submit refund or replacement requests for supervisor approval.'
      : personaKey === 'warehouse_manager' || (isWarehouse && !personaKey)
        ? 'Receive units and record inspections for analyst cases — refund and replacement paths use the same steps.'
        : personaKey === 'returns_supervisor' || approvalsUi
          ? 'Approve or reject analyst refund and replacement requests. The analyst emails the customer after your decision.'
          : `${persona.headerTagline}.`

  return (
    <div className="workspace-shell flex min-h-dvh flex-col">
      <WorkspaceNav />
      <div className="shrink-0 border-b border-stone-200 bg-white px-4 py-6 sm:px-6">
        <p className={panelTitle}>Workspace</p>
        <div className="mt-1 flex flex-wrap items-center gap-3">
          <h1 className="text-xl font-semibold text-stone-900">{heading}</h1>
          <LayoutDashboard className="size-5 text-accent-600" strokeWidth={1.75} aria-hidden />
        </div>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-stone-600">
          {blurb}{' '}
          <Link to="/workspace" className="text-accent-700 underline-offset-2 hover:underline">
            Open agent
          </Link>
        </p>
        <div className="mt-4">
          <button
            type="button"
            className={button('secondary', 'sm')}
            disabled={loading}
            onClick={() => refresh()}
          >
            <RefreshCw className={`size-4 ${loading ? 'animate-spin' : ''}`} aria-hidden />
            Refresh
          </button>
        </div>
      </div>

      <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-8 sm:px-6">
        {error && (
          <p className="mb-4 rounded-lg border border-red-200 bg-red-50 px-3 py-2.5 text-sm text-red-700" role="alert">
            {error}
          </p>
        )}
        {loading && !data && (
          <div className="flex items-center gap-2 text-sm text-stone-500">
            <Loader2 className="size-4 animate-spin" aria-hidden />
            Loading dashboard…
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
